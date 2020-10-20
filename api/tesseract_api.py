import os
import sys
from threading import Thread
from time import sleep
from telegram.error import TimedOut
from multiprocessing import Queue

tesseract_path = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(os.path.abspath(tesseract_path + '../'))

from api.tesseract_core import TesseractCore
from api.sql_queuer import sql_load, sql_insert, sql_delete


class TesseractAPI(TesseractCore):
    """Telegram API"""
    def __init__(self, threading=False):
        super().__init__()
        self.threading = threading
        self.queue = Queue()
        self._load_sql()

    def _load_sql(self):
        dataset = sql_load()
        print('saved queue size:', len(dataset))
        for data in dataset:
            self.queue.put(data)

    def start_queue_master(self):
        t = Thread(target=self._queue_master)
        t.daemon = True
        t.start()

    def _queue_master(self):
        while True:
            data = self.queue.get()
            print('queue: data was received')
            if self.threading:
                thr = Thread(target=self._bot_master, args=(data,))
                thr.daemon = True
                thr.start()
            else:
                self._bot_master(data)

    def _bot_master(self, data):
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
                sql_delete(data)
                data.update({'chats': save_chats, 'timeout': 60})
                self.put_queue(data)
            except FileNotFoundError as e:
                sql_delete(data)
                err_data = {'command': 'send_message', 'chat': 'test', 'text': e.__str__()}
                self.put_queue(err_data)
        sql_delete(data)
        if data['command'] == 'send_document' and os.path.exists(data['filepath']):
            os.remove(data['filepath'])

    def put_queue(self, data):
        self.queue.put(data)
        sql_insert(data)


def _get_msg_content(data):
    if data['command'] == 'send_message':
        return {'text': data['text']}
    elif data['command'] == 'send_document':
        return {'document': open(data['filepath'], 'rb')}
