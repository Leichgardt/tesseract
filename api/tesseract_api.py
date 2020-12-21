import os
import sys
from datetime import datetime
import requests
from threading import Thread
from time import sleep
from telegram.error import TimedOut
from multiprocessing import Queue

project_path = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '../')
sys.path.append(project_path)

from api.tesseract_core import TesseractCore
from api.sql_queuer import sql_load, sql_insert, sql_delete


TELEGRAM_URL = 'https://api.telegram.org/bot{}/{}'


class TesseractAPI(TesseractCore):
    """Telegram API"""
    def __init__(self, threading=False, upload_dir='upload'):
        super().__init__()
        self.threading = threading
        self.upload_dir = upload_dir
        self.queue = Queue()
        self._load_sql()

    def _load_sql(self):
        dataset = sql_load()
        print('saved queue size:', len(dataset))
        for data in dataset:
            self.queue.put(data)

    def start_queue_master(self):
        t1 = Thread(target=self._queue_master)
        t1.daemon = True
        t1.start()
        t2 = Thread(target=self._upload_cleaner)
        t2.daemon = True
        t2.start()

    def _upload_cleaner(self):
        upload_path = os.path.join(project_path, self.upload_dir)
        while True:
            sleep(60)
            if os.path.isdir(upload_path):
                for filename in os.listdir(upload_path):
                    if os.path.isfile(filename):
                        ctime = os.path.getctime(os.path.join(upload_path, filename))
                        cdate = datetime.fromtimestamp(ctime)
                        diftime = datetime.now() - cdate
                        if diftime.total_seconds() > 600.0:
                            os.remove(os.path.join(upload_path, filename))

    def _queue_master(self):
        while True:
            data = self.queue.get()
            print('queue data was received', data)
            if self.threading:
                print('threading mode: 1')
                thr = Thread(target=self._bot_master, args=(data,))
                thr.daemon = True
                thr.start()
            else:
                print('threading mode: 0')
                self._bot_master(data)

    def _bot_master(self, data):
        group = data.get('chat')
        cid = data.get('chat_id')
        chats = []
        if group in self.subs.keys():
            chats = self.subs[group]
        if cid is not None:
            chats.append(cid)
        save_chats = chats.copy()
        if data.get('bot') == 'IronnetAdminBot':
            cmd = 'sendMessage?disable_web_page_preview=1&parse_mode={}'.format(data['parse_mode'])
            cmd += '&chat_id={}&text={}'
            for chat_id in chats:
                url = TELEGRAM_URL.format(self.token['IronnetAdminBot'], cmd.format(chat_id, data['text']))
                res = requests.post(url)
                if not res.ok:
                    sql_delete(data)
                    raise ConnectionError('Tesseract: sending msg from "IronnetAdminBot" failed. Data:\n%s' % str(data))
            sql_delete(data)
        else:
            bot_cmd = eval('self.bot.' + data['command'])
            timeout = data.get('timeout', 10)

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
                    break
                except FileNotFoundError as e:
                    sql_delete(data)
                    err_data = {'command': 'send_message', 'chat': 'test', 'text': e.__str__()}
                    self.put_queue(err_data)
            sql_delete(data)

    def put_queue(self, data):
        if data.get('bot') == 'IronnetAdminBot' and data.get('command') not in ['send_message']:
            raise ValueError('Bot "{}" doesn\'t support command "{}"'.format(data.get('bot'), data.get('command')))
        self.queue.put(data)
        sql_insert(data)
        return 1


def _get_msg_content(data):
    if data['command'] == 'send_message':
        return {'text': data['text'], 'parse_mode': data['parse_mode']}
    elif data['command'] == 'send_document':
        return {'document': open(data['filepath'], 'rb')}
