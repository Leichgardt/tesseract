from functools import wraps
from flask import Flask, render_template, request
import os
import traceback
from werkzeug.utils import secure_filename
from api.tesseract_bot import TesseractBot

UPLOAD_FOLDER = 'uploads'
project_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__))) + '/'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bot = TesseractBot()
bot.threading = False
bot.upload_dir = UPLOAD_FOLDER
bot.start_queue_master()


def request_handler(request_func):
    @wraps(request_func)
    def super_wrapper():
        try:
            print('Request received. Processing...')
            return request_func(), 200
        except KeyError as e:
            return {'response': -1, 'error': e.__str__()}, 400
        except ValueError as e:
            return {'response': 0, 'error': e.__str__()}, 400
        except Exception as e:
            print('[{}]:'.format(request_func.__name__))
            text = 'Tesseract error:\n{}'.format(traceback.format_exc())
            data = {'command': 'send_message', 'chat': 'test', 'text': text}
            bot.put_queue(data)
            return {'response': -999, 'error': e.__str__()}, 500
    return super_wrapper


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/get_list', methods=['GET', 'POST'])
def get_list():
    try:
        return {'subs': bot.subs_output(), 'groups': bot.groups_output()}
    except Exception as e:
        print('[get_list]:', e)
        return {'result': [-1]}


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
    _check_payload(group, chat_id, bot_name)
    if json_data.get('text', '') == '':
        raise ValueError('empty text')
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
        _check_payload(group, chat_id, bot_name)
        if len(list(request.files.values())) == 0:
            raise ValueError('empty data')
        _check_folder()
        for f in request.files.values():
            filename = secure_filename(f.filename)
            filepath = os.path.join(project_dir, app.config['UPLOAD_FOLDER'], filename)
            f.save(filepath)
            print(f, filename, filepath, sep='\n - ')
            data = {'command': 'send_document', 'chat': group, 'chat_id': chat_id, 'filepath': filepath}
            bot.put_queue(data)
        return {'response': 1}
    return {'response': 0}


def _check_payload(group, chat_id, bot_name):
    if bot_name not in bot.token.keys():
        raise KeyError(f'Bot "{bot_name}" doesn\'t exist')
    elif (group in ['', None] or group not in bot.subs.keys()) and not chat_id:
        raise KeyError(f'Group "{group}" doesn\'t exist')
    elif chat_id in ['', None] and not group:
        raise KeyError(f'No "chat_id" or "group" specified')


def _check_folder():
    if not os.path.isdir(project_dir + UPLOAD_FOLDER):
        print('Making upload directory')
        os.mkdir(project_dir + UPLOAD_FOLDER)
