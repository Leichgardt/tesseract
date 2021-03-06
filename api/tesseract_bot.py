import os
import sys
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

tesseract_path = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(os.path.abspath(tesseract_path + '../'))

from api.tesseract_api import TesseractAPI


class TesseractBot(TesseractAPI):
    """Telegram Bot"""
    def __init__(self, logger=None):
        super().__init__(logger=logger)

        self.updater = Updater(token=self.token['tesseract'], use_context=True)
        dispatcher = self.updater.dispatcher

        start_handler = CommandHandler('start', self._start)
        dispatcher.add_handler(start_handler)

        start_handler = CommandHandler('hello', self._start)
        dispatcher.add_handler(start_handler)

        help_handler = CommandHandler('help', self._help)
        dispatcher.add_handler(help_handler)

        iam_handler = CommandHandler('iam', self._iam)
        dispatcher.add_handler(iam_handler)

        sub_handler = CommandHandler('subscribe', self._subscribe)
        dispatcher.add_handler(sub_handler)

        unsub_handler = CommandHandler('unsubscribe', self._unsubscribe)
        dispatcher.add_handler(unsub_handler)

        groups_handler = CommandHandler('groups', self._groups)
        dispatcher.add_handler(groups_handler)

        set_group_handler = CommandHandler('set_group', self._set_group)
        dispatcher.add_handler(set_group_handler)

        leave_group_handler = CommandHandler('leave_group', self._leave_group)
        dispatcher.add_handler(leave_group_handler)

        unknown_handler = MessageHandler(Filters.command, self._unknown)
        dispatcher.add_handler(unknown_handler)

        self.updater.start_polling()

    def _start(self, update, context):
        text = "Tesseract are greetings you.\n/subscribe\n/help"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text, timeout=60)

    def _help(self, update, context):
        text = "Command list:\n/iam\n/subscribe\n/unsubscribe\n/groups\n/set_group NewGroup\n/leave_group Group"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text, timeout=60)

    def _iam(self, update, context):
        chat_id = str(update.effective_chat.id)
        text = f"Chat ID: {chat_id}\nGroups:\n"
        for group, subs in self.subs.items():
            if chat_id in subs:
                text += f' - {group}'
        context.bot.send_message(chat_id=chat_id, text=text, timeout=60)

    def _subscribe(self, update, context):
        chat_id = str(update.effective_chat.id)
        if chat_id not in self.subs['all']:
            self.subs['all'].append(chat_id)
            text = "Subscribed. You are in group 'all'\n"
            if len(self.subs.keys()) > 1:
                text += 'Select your new group\n'
                for group in self.subs.keys():
                    text += f"/set_group {group}\n"
            text += "Also you can create new group for this chat\n/set_group NewGroup"
            self._save_subs()
            context.bot.send_message(chat_id=chat_id, text=text, timeout=60)
        else:
            context.bot.send_message(chat_id=chat_id, text="You are already a subscriber.\nYou can choose new Group\n/groups", timeout=60)
        self.logger.info(f'Subscribed {chat_id}')

    def _unsubscribe(self, update, context):
        chat_id = str(update.effective_chat.id)
        if chat_id in self.subs['all']:
            for group in self.subs.keys():
                if chat_id in self.subs[group]:
                    self.subs[group].remove(chat_id)
                if len(self.subs[group]) == 0:
                    self.subs.pop(group)
            self._save_subs()
            context.bot.send_message(chat_id=chat_id, text="Unsubscribed.", timeout=60)
        else:
            context.bot.send_message(chat_id=chat_id, text="You are not a subscriber.", timeout=60)
        self.logger.info(f'Unsubscribed {chat_id}')

    def _set_group(self, update, context):
        chat_id = str(update.effective_chat.id)
        group = update.message.text.replace('/set_group', '').strip()
        self.logger.info(f'Set #{group}# for {chat_id}')

        if group == '':
            context.bot.send_message(chat_id=chat_id, text="Run command with /set_group NewGroup", timeout=60)
            return

        if chat_id not in self.subs['all']:
            self.subs['all'].append(chat_id)

        if group not in self.subs.keys():  # если группы нет
            self.subs.update({group: [chat_id]})
            context.bot.send_message(chat_id=chat_id, text=f"New group '{group}' created", timeout=60)
        elif chat_id not in self.subs[group]:  # если группа есть
            self.subs[group].append(chat_id)
            context.bot.send_message(chat_id=chat_id, text=f"Added in group '{group}'", timeout=60)
        else:  # если есть в группе
            context.bot.send_message(chat_id=chat_id, text="You are already in the group", timeout=60)
        self._save_subs()

    def _leave_group(self, update, context):
        chat_id = str(update.effective_chat.id)
        group = update.message.text.replace('/leave_group', '').strip()
        self.logger.info(f'Leave {chat_id} from #{group}#')

        if group == '':
            context.bot.send_message(chat_id=chat_id, text="Run command with /leave_group NewGroup", timeout=60)
            return

        if group == 'all':
            for group in self.subs.keys():
                self.subs[group].remove(chat_id)
                context.bot.send_message(chat_id=chat_id, text=f"You left all groups", timeout=60)
        elif group in self.subs.keys():
            self.subs[group].remove(chat_id)
            context.bot.send_message(chat_id=chat_id, text=f"You left '{group}'", timeout=60)
        else:
            context.bot.send_message(chat_id=chat_id, text=f"Group '{group}' doesn't exist", timeout=60)
        if len(self.subs[group]) == 0:
            self.subs.pop(group)
        self._save_subs()

    def _groups(self, update, context):
        chat_id = str(update.effective_chat.id)
        text = 'Groups:\n'
        for group in self.subs.keys():
            text += f" - {group}\n"
        text += 'To join in the group run /set_group Group'
        context.bot.send_message(chat_id=chat_id, text=text, timeout=60)

    def _unknown(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command.", timeout=60)


if __name__ == "__main__":
    bot = TesseractBot()
