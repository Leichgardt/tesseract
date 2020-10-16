import os
import sys
from threading import Thread
from multiprocessing import Queue

tesseract_path = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(os.path.abspath(tesseract_path + '../'))

from api.tesseract_core import TesseractCore


class TesseractAPI(TesseractCore):
    """Telegram API"""
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        t = Thread(target=self._queue_master)
        t.daemon = True
        t.start()

    def _queue_master(self):
        while True:
            cmd = self.queue.get()
            if cmd['command'] == 'sendMessage':
                thr = Thread(target=self.send_notify, args=(cmd['chat'], cmd['text']))
                # self.send_notify(cmd['chat'], cmd['text'])
            elif cmd['command'] == 'sendDocument':
                # self.send_file(cmd['chat'], cmd['document'], cmd['filepath'])
                thr = Thread(target=self.send_file, args=(cmd['chat'], cmd['filepath']))
            thr.daemon = True
            thr.start()

    def send_notify(self, header, text):
        for chat_id in self.subs[header]:
            self.bot.send_message(chat_id=chat_id, text=text, timeout=60)

    def send_file(self, header, filepath):
        for chat_id in self.subs[header]:
            # cmd = 'curl -v -F "chat_id={}" -F document=@{} https://api.telegram.org/bot{}/sendDocument'.format(
            #     chat_id, open(filepath, 'rb'), self.token
            # )
            # subprocess.Popen(cmd, shell=True)
            self.bot.send_document(chat_id=chat_id, document=open(filepath, 'rb'))
            os.remove(filepath)
