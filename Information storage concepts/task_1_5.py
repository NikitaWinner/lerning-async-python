import platform
import subprocess
from chardet import detect


def ping_service(service: str, count_of_pack: str) -> None:
    """ Функция выполняет пинг веб-ресурсов и преобразовает результаты
    из байтового в строковый (предварительно определив кодировку выводимых сообщений)
    :param service: веб-ресурс
    :param count_of_pack: кол-во пакетов для пинга
    """
    code = '-n' if platform.system().lower() == 'windows' else '-c'
    args = ['ping', code, count_of_pack, service]
    YA_PING = subprocess.Popen(args, stdout=subprocess.PIPE)
    for line in YA_PING.stdout:
        result = detect(line)
        line = line.decode(result['encoding']).encode('utf-8')
        print(line.decode('utf-8'))

URLS = ['yandex.ru', 'youtube.com']
for url in URLS:
    ping_service(url, '4')