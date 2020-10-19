import os
import sys
from threading import Thread
from time import sleep
from telegram.error import TimedOut
from multiprocessing import Queue

tesseract_path = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(os.path.abspath(tesseract_path + '../'))

from api.tesseract_core import TesseractCore
from api.sql_queuer import SQLMaster


class TesseractAPI(TesseractCore):
    """Telegram API"""
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        t = Thread(target=self._queue_master)
        t.daemon = True
        t.start()
        self.load_sql()

    def load_sql(self):
        sql = SQLMaster()
        dataset = sql.load_queue()
        print('saved queue size:', len(dataset))
        for data in dataset:
            self.queue.put(data)

    def _queue_master(self):
        sql = SQLMaster()
        while True:
            data = self.queue.get()
            print('queue: data was received -', data)
            sql.insert_queue(data)
            thr = Thread(target=self._bot_master, args=(data,))
            thr.daemon = True
            thr.start()

    def _bot_master(self, data):
        sql = SQLMaster()
        bot_cmd = eval('self.bot.' + data['command'])
        timeout = data.get('timeout', 10)
        chats = data.get('chats', self.subs[data.get('chat', 'test')])
        save_chats = chats.copy()

        for chat_id in chats:
            try:
                bot_data = {**_get_msg_content(data), 'chat_id': chat_id, 'timeout': timeout}
                bot_cmd(**bot_data)
                save_chats.remove(chat_id)
            except TimedOut:
                sleep(timeout // 5)
                data.update({'chats': save_chats, 'timeout': 60})
                self.queue.put(data)
                sql.insert_queue(data)
            except FileNotFoundError as e:
                err_data = {'command': 'send_message', 'chat': 'test', 'text': e.__str__()}
                self.queue.put(err_data)
                sql.insert_queue(err_data)
        sql.delete_queue(data)
        super_cleaner(data)


def super_cleaner(data):
    if data['command'] == 'send_document' and os.path.exists(data['filepath']):
        os.remove(data['filepath'])


def _get_msg_content(data):
    if data['command'] == 'send_message':
        return {'text': data['text']}
    elif data['command'] == 'send_document':
        return {'document': open(data['filepath'], 'rb')}
