import json
import os
import logging
import telegram.bot
from telegram.ext import Updater
from telegram.utils.request import Request
from api.configer import Configer

tesseract_path = os.path.dirname(os.path.abspath(__file__)) + '/'


class TesseractCore:
    """Telegram Bot"""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('tesseract')
        self.last_ari_msg = 0
        self.last_rev_msg = 0
        self.subs = {'all': []}

        if os.path.exists(tesseract_path + 'subs.json'):
            self._load_subs()

        cfg = Configer().upload(module='Tesseract')
        self.token = {'tesseract': cfg('token-tesseract', ''),
                      'IronnetAdminBot': cfg('token-ironnetadminbot', '')}
        del cfg

        request = Request(con_pool_size=64)
        self.bot = telegram.bot.Bot(token=self.token['tesseract'], request=request)
        self.bot.getUpdates(timeout=5)
        self.updater = Updater(bot=self.bot, use_context=True)

    def subs_output(self):
        return json.dumps(self.subs, indent=8, sort_keys=True)

    def groups_output(self):
        return list(self.subs.keys())

    def _load_subs(self):
        self.subs = json.load(open(tesseract_path + 'subs.json', 'r'))

    def _save_subs(self):
        json.dump(self.subs, open(tesseract_path + 'subs.json', 'w'))
