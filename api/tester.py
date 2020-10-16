import requests as r

server = 'http://127.0.0.1:5420/'


def send_file():
    url = server + 'api/bot_send_file'

    payload = {'header': 'test'}
    files = {'file': open('subs.json', 'rb')}
    print(files)
    res = r.post(url, data=payload, files=files, verify=False)
    print(res.text)


def send_notify():
    url = server + 'api/bot_notify'

    payload = {'header': 'test', 'text': 'kek'}
    res = r.post(url, json=payload, verify=False)
    print(res.text)


if __name__ == '__main__':
    # send_notify()
    send_file()
