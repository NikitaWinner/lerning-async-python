"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping
будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел
должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять
их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес
сетевого узла должен создаваться с помощью функции ip_address().

Внимание! Аргументом сабпроцеса должен быть список, а не строка!!!
Для уменьшения времени работы скрипта при проверке нескольких ip-адресов,
решение необходимо выполнить с помощью потоков.
"""
import os
import platform
import subprocess
import time
import threading
from ipaddress import ip_address
from pprint import pprint

# словарь с результатами
result = {'Reachable': [],
          "Unreachable": []}

# заглушка, чтобы поток не выводился на экран
DNULL = open(os.devnull, 'w')


def check_is_ipaddress(value: str) -> ip_address:
    """ Проверка является ли введённое значение IP адресом
    :param value: Присланное значение, IP-адрес в виде строки.
    :return ipv4: Полученный ip адрес из переданного значения, экземпляр класса IPv4Address.
        Exception ошибка при невозможности получения ip адреса из значения.
    """
    try:
        ipv4 = ip_address(value)
    except ValueError:
        raise Exception('Некорректный ip адрес')
    return ipv4


def ping(ipv4, result: dict, get_list: bool) -> str:
    """ Вспомогательная функция создания процесса проверки доступности хостов.
    :param ipv4: Ip-адрес, экземпляр класса IPv4Address.
    :param result: Словарь, для хранения результатов проверки хостов.
    :param get_list: Флаг, нужно ли отдать результат в виде словаря.
    :return: Строка с информацией о доступности хоста.
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    response = subprocess.Popen(["ping", param, '1', '-w', '1', str(ipv4)],
                                stdout=subprocess.PIPE)
    if response.wait() == 0:
        result["Reachable"].append(str(ipv4))
        res = f"{ipv4} - Узел доступен"
        if not get_list:
            print(res)
        return res
    else:
        result["Unreachable"].append(str(ipv4))
        res = f"{str(ipv4)} - Узел недоступен"
        if not get_list:
            print(res)
        return res


def host_ping(hosts_list: list, get_list: bool = False) -> None | dict:
    """ Проверка доступности хостов и создание потока.
    :param hosts_list: Список хостов.
    :param get_list: Признак нужно ли отдать результат в виде словаря.
    :return Словарь результатов проверки, если требуется.
    """
    print("Начинаю проверку доступности узлов...")
    threads = []
    # Проверка, является ли значение ip-адресом.
    for host in hosts_list:
        try:
            ipv4 = check_is_ipaddress(host)
        except Exception as e:
            print(f'{host} - {e} воспринимаю как доменное имя')
            ipv4 = host

        thread = threading.Thread(target=ping, args=(ipv4, result, get_list), daemon=True)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    if get_list:
        return result


if __name__ == '__main__':
    # список проверяемых хостов
    hosts_list = ['192.168.8.1', '8.8.8.8', 'yandex.ru', 'google.com',
                  '0.0.0.1', '0.0.0.2', '0.0.0.3', '0.0.0.4', '0.0.0.5',
                  '0.0.0.6', '0.0.0.7', '0.0.0.8', '0.0.0.9', '0.0.1.0']
    start = time.time()
    host_ping(hosts_list)
    end = time.time()
    print(f'Total time: {round(end - start, 2)} sec.')
    pprint(result)
