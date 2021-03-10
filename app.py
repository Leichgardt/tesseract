__author__ = 'Leichgardt'

from functools import wraps
from flask import Flask, render_template, request, send_from_directory
import os
import traceback
import logging
from werkzeug.utils import secure_filename
from api.tesseract_bot import TesseractBot
from api.configer import Configer

UPLOAD_FOLDER = 'uploads'
project_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__))) + '/'

f_format = logging.Formatter('[%(asctime)s] %(levelname)s - in %(filename)s: %(funcName)s(%(lineno)d)\n%(message)s\n')
s_format = logging.Formatter('%(levelname)s in %(filename)s(%(lineno)d) - %(message)s')
s_handler = logging.StreamHandler()
s_handler.setLevel(logging.INFO)
s_handler.setFormatter(s_format)
f_handler = logging.FileHandler('/var/log/iron/tesseract.log')
f_handler.setLevel(logging.WARNING)
f_handler.setFormatter(f_format)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.logger = logging.getLogger('flask')
app.logger.setLevel(logging.INFO)
app.logger.addHandler(s_handler)
app.logger.addHandler(f_handler)

bot = TesseractBot(logger=app.logger)
bot.threading = False
bot.upload_dir = UPLOAD_FOLDER
bot.start_queue_master()
cfg = Configer().upload(module='Paladin')
host_domain = cfg('domain')
main_domain = cfg('main-domain')
del cfg

app.logger.info('Tesseract launched! Welcome to job!')


def request_handler(request_func):
    @wraps(request_func)
    def super_wrapper(*args, **kwargs):
        try:
            extra = f' with {args}' if args else ''
            extra += f' with {kwargs}' if kwargs else ''
            app.logger.info(f'[{request_func.__name__}] request received{extra}')
            return request_func(*args, **kwargs), 200
        except KeyError as e:
            return {'response': -1, 'error': e.__str__()}, 400
        except ValueError as e:
            return {'response': 0, 'error': e.__str__()}, 400
        except Exception as e:
            app.logger.error('Exception:', traceback.format_exc())
            return {'response': -999, 'error': e.__str__()}, 500
    return super_wrapper


@app.route('/static/<path:path>')
def static_request(path):
    return send_from_directory('static', path)


@app.route('/')
def index():
    about = 'Сервис для достоверной отправки сообщений в группы чатов Telegram'
    return render_template('index.html',
                           title='Tesseract',
                           about=about,
                           version='0.4.0',
                           domain=main_domain,
                           main_url=host_domain + '/tesseract')


@app.route('/api/get_list', methods=['GET', 'POST'])
def get_list():
    try:
        return {'response': 1, 'subs': bot.subs_output(), 'groups': bot.groups_output()}
    except Exception as e:
        app.logger.error('[get_list]:', e)
        return {'response': 1, 'result': [-1]}


@app.route('/api/notify', methods=['POST'])
@app.route('/api/send_message', methods=['POST'])
@app.route('/api/bot_notify', methods=['POST'])
@app.route('/api/bot_send_message', methods=['POST'])
@request_handler
def bot_notify():
    json_data = request.get_json()
    group = json_data.get('header', None) or json_data.get('chat', None) or json_data.get('group', None)
    chat_id = json_data.get('chat_id', None)
    bot_name = json_data.get('bot', 'tesseract')
    passcode, res = _check_payload(group, chat_id, bot_name)
    if not passcode:
        return {'response': 0, 'error': res}
    if json_data.get('text', '') == '':
        return {'response': 0, 'error': 'empty text'}
    if 'header' in json_data.keys():
        json_data.pop('header')
    if 'group' in json_data.keys():
        json_data.pop('group')
    new = {'chat': group, 'chat_id': chat_id}
    data = {**json_data, 'command': 'send_message'}
    data.update(new)
    bot.put_queue(data)
    return {'response': 1}


@app.route('/api/send_file', methods=['POST'])
@app.route('/api/send_document', methods=['POST'])
@app.route('/api/bot_send_file', methods=['POST'])
@app.route('/api/bot_send_document', methods=['POST'])
@request_handler
def bot_send_file():
    if 'multipart/form-data' in request.content_type:
        group = request.form.get('header', None) or request.form.get('chat', None) or request.form.get('group', None)
        chat_id = request.form.get('chat_id', None)
        bot_name = request.form.get('bot', 'tesseract')
        passcode, res = _check_payload(group, chat_id, bot_name)
        if not passcode:
            return {'response': 0, 'error': res}
        if len(list(request.files.values())) == 0:
            return {'response': 0, 'error': 'empty data'}
        _check_folder()
        for f in request.files.values():
            filename = secure_filename(f.filename)
            filepath = os.path.join(project_dir, app.config['UPLOAD_FOLDER'], filename)
            f.save(filepath)
            app.logger.info(f, filename, filepath, sep='\n - ')
            data = {'command': 'send_document', 'chat': group, 'chat_id': chat_id, 'filepath': filepath}
            bot.put_queue(data)
        return {'response': 1}
    return {'response': 0}


def _check_payload(group, chat_id, bot_name):
    if bot_name not in bot.token.keys():
        return 0, f'Bot "{bot_name}" doesn\'t exist'
    elif (group in ['', None] or group not in bot.subs.keys()) and not chat_id:
        return 0, f'Group "{group}" doesn\'t exist'
    elif chat_id in ['', None] and not group:
        return 0, f'No "chat_id" or "group" specified'
    return 1, ''


def _check_folder():
    if not os.path.isdir(project_dir + UPLOAD_FOLDER):
        app.logger.info('Making upload directory')
        os.mkdir(project_dir + UPLOAD_FOLDER)
