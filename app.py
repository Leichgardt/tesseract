import os
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from api.tesseract_bot import TesseractBot

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'json', 'rar', 'zip', 'tag', 'gz', '7z'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bot = TesseractBot()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/api/get_list', methods=['GET', 'POST'])
def get_list():
    try:
        return {'subs': bot.subs_output(), 'groups': bot.groups_output()}
    except Exception as e:
        print('[get_list]:', e)
        return {'result': [-1]}


@app.route('/api/bot_notify', methods=['POST'])
def bot_notify():
    print('Request received. Processing...')
    try:
        if request.method == 'POST':
            json_data = request.get_json()
            header = json_data['header']
            text = json_data['text']
            bot.send_notify(header, text)
            return {'response': 1}
    except Exception as e:
        print('[bot_notify]:', e)
        return {'response': -1}


@app.route('/api/bot_send_file', methods=['POST'])
def bot_send_file():
    print('Request received. Processing...')
    try:
        if request.method == 'POST':
            if 'multipart/form-data' in request.content_type:
                header = request.form.get('header', '')
                if header == '':
                    return {'response': 0}
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    print(file, filename, filepath, sep='\n - ')
                    bot.send_file(header, open(filepath, 'rb'))
                    os.remove(filepath)
                    return {'response': 1}
                return {'response': 0}
    except Exception as e:
        print('[bot_send_file]:', e)
        return {'response': -1}


if __name__ == '__main__':
    app.run()
