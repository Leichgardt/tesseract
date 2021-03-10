import os
import sys
from datetime import datetime
import requests
from threading import Thread
from time import sleep
from telegram.error import TimedOut, NetworkError
from multiprocessing import Queue

project_path = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '../')
sys.path.append(project_path)

from api.tesseract_core import TesseractCore
from api.sql_queuer import sql_load, sql_insert, sql_delete


TELEGRAM_URL = 'https://api.telegram.org/bot{}/{}'


class TesseractAPI(TesseractCore):
    """Telegram API"""
    def __init__(self, logger=None, threading=False, upload_dir='upload'):
        super().__init__(logger=logger)
        self.threading = threading
        self.upload_dir = upload_dir
        self.queue = Queue()
        self._load_sql()
        self._historic = Historic()

    def _load_sql(self):
        dataset = sql_load()
        self.logger.info(f'Saved queue size: {len(dataset)}')
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
            self.logger.info(f'queue data was received: {data}')
            if self.threading:
                thr = Thread(target=self._bot_master, args=(data,))
                thr.daemon = True
                thr.start()
            else:
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
        if data.get('bot') != 'tesseract':
            cmd = 'sendMessage?disable_web_page_preview=1&parse_mode={}'.format(data['parse_mode'])
            cmd += '&chat_id={}&text={}'
            for chat_id in chats:
                url = TELEGRAM_URL.format(self.token[data.get('bot')], cmd.format(chat_id, data['text']))
                res = requests.post(url)
                if not res.ok:
                    sql_delete(data)
                    msg = 'Sending msg from bot "%s" failed. Data:\n%s' % (data.get('bot'), str(data))
                    self.logger.warning(msg)
                    break
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
                    self.logger.warning(f'Timed out on {data}')
                    self._master_handler(data, timeout // 5, save_chats)
                    break
                except NetworkError:
                    self.logger.warning(f'Network downed on {data}')
                    self._master_handler(data, timeout, save_chats)
                except FileNotFoundError as e:
                    sql_delete(data)
                    err_data = {'command': 'send_message', 'chat': 'test', 'text': e.__str__()}
                    self.put_queue(err_data)
                except Exception as e:
                    self.logger.error(e)
                    sql_delete(data)
                    err_data = {'command': 'send_message', 'chat': 'test', 'text': e.__str__()}
                    self.put_queue(err_data)
                    break
                else:
                    self._historic.write(data['command'], f'{chat_id}', bot_data.get('text', bot_data.get('document', '')))
            sql_delete(data)

    def _master_handler(self, data, timeout, save_chats):
        sql_delete(data)
        sleep(timeout)
        data.update({'chats': save_chats, 'timeout': 60})
        self.put_queue(data)

    def put_queue(self, data):
        data.update({'bot': data.get('bot', 'tesseract')})
        if data.get('bot') != 'tesseract' and data.get('command') not in ['send_message']:
            self.logger.warning('Bot "{}" doesn\'t support command "{}"'.format(data.get('bot'), data.get('command')))
            return 0
        self.queue.put(data)
        sql_insert(data)
        return 1

    def get_history(self):
        return self._historic.read()


def _get_msg_content(data):
    if data['command'] == 'send_document':
        return {'document': open(data['filepath'], 'rb')}
    else:
        return data


class Historic:
    def __init__(self):
        self.filepath = os.path.abspath(os.path.dirname(os.path.abspath(__file__))) + '/history.txt'

    def write(self, cmd, chat, data):
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new = '{0} | {1:15.15} | {2:>15.15} | {3}'.format(date, cmd, str(chat)[-10:], data)
        lines = []
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                lines = f.readlines()
        lines = [line.replace('\n', '') for line in lines if line or line != '\n']
        lines.reverse()
        lines = lines[-19:]
        lines.append(new)
        lines.reverse()
        lines = [line + '\n' for line in lines]
        with open(self.filepath, 'w') as f:
            f.writelines(lines)

    def read(self):
        lines = []
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                lines = f.readlines()
        return ''.join(lines)
