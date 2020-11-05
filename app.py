from functools import wraps
from flask import Flask, render_template, request
import os
import traceback
from werkzeug.utils import secure_filename
from api.tesseract_bot import TesseractBot

UPLOAD_FOLDER = 'uploads'
project_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bot = TesseractBot()
bot.threading = False
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
            data = {'command': 'sendMessage', 'chat': 'test', 'text': text}
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


@app.route('/api/bot_notify', methods=['POST'])
@app.route('/api/bot_send_message', methods=['POST'])
@request_handler
def bot_notify():
    if request.method == 'POST':
        json_data = request.get_json()
        header = json_data.get('header', None) or json_data.get('chat', None)
        text = json_data.get('text', '')
        if text == '':
            raise ValueError('empty text')
        _check_chat(header)
        data = {'command': 'send_message', 'chat': header, 'text': text}
        bot.put_queue(data)
        return {'response': 1}


@app.route('/api/bot_send_file', methods=['POST'])
@app.route('/api/bot_send_document', methods=['POST'])
@request_handler
def bot_send_file():
    if request.method == 'POST':
        if 'multipart/form-data' in request.content_type:
            header = request.form.get('header', None) or request.form.get('chat', None)
            _check_chat(header)
            if len(list(request.files.values())) == 0:
                raise ValueError('empty data')
            for f in request.files.values():
                filename = secure_filename(f.filename)
                filepath = os.path.join(project_dir, app.config['UPLOAD_FOLDER'], filename)
                f.save(filepath)
                print(f, filename, filepath, sep='\n - ')
                data = {'command': 'send_document', 'chat': header, 'filepath': filepath}
                bot.put_queue(data)
            return {'response': 1}
        return {'response': 0}


def _check_chat(header):
    if header == '' or header is None or header not in bot.subs.keys():
        raise KeyError(f'chat -{header}- does not exist')


if __name__ == '__main__':
    app.run()
