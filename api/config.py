import os
import requests
import re


class Configer:

    """
    Класс для загрузки конфигураций из файла.
    Пример содержания файла config.txt:

    ###################
    [TelegramBot]
    # token to bot access
    User=tele_user
    Token=xxxyyyzzz

    [Lanbilling]
    Host=192.168.1.10
    User=admin
    Password=123

    ###################

    Вызов объекта класса выдаст загруженные данные или, если данных не было, выдаст установленное value
    >>> cfg = Configer(url='/url/to/config.txt').upload(module='Lanbilling')
    >>> print('user =' cfg('user', 'MyUsername'))
    >>> print('url =', cfg('url', 'http://some.url/'))

    Вывод:
    1 user = admin
    2 url = http://some.url/

    """

    def __init__(self, **kwargs):
        self.url = kwargs.get('url', 'localhost')
        self.config_list = {}
        self.user = ''
        self.__passwd = ''

    def __getitem__(self, item):
        if item not in self.config_list.keys():
            self.config_list.update({item: None})
        return self.config_list[item]

    def __call__(self, param, value=None):
        if param not in self.config_list.keys():
            self.config_list.update({param: value})
        return self.config_list[param]

    def config_params(self, filepath=os.path.dirname(os.path.abspath(__file__)) + '/config_params.txt'):
        with open(filepath, 'r') as f:
            text = [line.replace('\n', '').strip() for line in f.readlines()]
            self.url = text[0]
            self.user = text[1]
            self.__passwd = text[2]

    def upload(self, **kwargs):
        self.config_params()
        config_url = kwargs.get('url', self.url)
        config_module = f"[{kwargs.get('module')}]\n"
        print("Uploading configuration for {} module from {}".format(config_module.replace('\n', ''), config_url))
        self.config_list = {}
        with requests.get(config_url, auth=(self.user, self.__passwd)) as r:
            if r.status_code != 200:
                print(f"Server doesn't respond.\n{config_url}\nPrevious configurations are not deleted.")
                return self
            r.encoding = r.apparent_encoding
            text = re.split("([^\n]*\n)", r.text)[1::2]
            if config_module not in text:
                print(f"Cannot find module [{config_module}] into config.txt.")
                return self
            start = text.index(config_module) + 1 if config_module in text else 0
            end = len(text)
            for i, line in enumerate(text[start:]):
                if ']\n' in line:
                    end = start + i - 1
                    break
            for line in text[start:end]:
                if line[0] == '#':
                    continue
                elif line != '\n':
                    item = line.replace('\n', '').split('=')
                    if ',' in item[1]:
                        item[1] = item[1].split(',')
                    self.config_list.update({item[0].lower(): item[1]})
        return self


if __name__ == "__main__":
    cfg = Configer()
    cfg.upload(module='Lanbilling')
    [print(item) for item in cfg.config_list.items()]
