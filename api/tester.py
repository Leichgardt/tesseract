import requests

url = 'http://127.0.0.1/tesseract/api/bot_send_file'
s = requests.Session()

payload = {'header': 'all', 'text': 'kek'}
files = {'file': open('subs.json', 'rb')}
res = s.post(url, data=payload, files=files, verify=False)
print(res.json()['response'])
