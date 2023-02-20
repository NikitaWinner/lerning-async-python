"""Программа-сервер"""

import sys
import json
import socket
import select
import logging
import argparse
from decorators import Log
from datetime import datetime
import logs.config_server_log
from common.utils import get_message, send_message
from exceptions import IncorrectDataRecivedError, NonDictInputError
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, DEFAULT_PORT, MAX_CONNECTIONS, ERROR, MESSAGE_TEXT, MESSAGE, \
    SENDER, RESPONSE_200, RESPONSE_400, DESTINATION, EXIT

# Инициализация логирования сервера.
SERVER_LOGGER = logging.getLogger('server')


@Log(SERVER_LOGGER)
def process_client_message(message: dict, messages_list: list,
                           client, clients: list, registered_names: dict):
    """ Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
    проверяет корректность, отправляет клиенту словарь-ответ, если необходимо.
    :param message: Сообщение в виде словаря принятое от клиента по протоколу JIM.
    :param messages_list: Список для хранения очереди сообщений.
    :param client: Файловый дескриптор, готовый к вводу (готовый принять сообщение от сервера).
    :param clients: Список клиентских сокетов, с кем установленно соединение.
    :param names: Словарь, для имен пользователей в качесве ключа и их сокетов в качестве значения.
    """
    SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {message}')
    # Принимаем и отвечаем на собщение о присутствии.
    if ACTION in message and message[ACTION] == PRESENCE and \
            TIME in message and USER in message:
        # Если такой пользователь ещё не зарегистрирован,
        # регистрирую, иначе отправляю ответ 400 и завершаю соединение.
        if message[USER][ACCOUNT_NAME] not in registered_names.keys():
            registered_names[message[USER][ACCOUNT_NAME]] = client  # {'client_name': client_socket}
            send_message(client, RESPONSE_200)
            return RESPONSE_200
        else:
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            send_message(client, response)
            clients.remove(client)
            client.close()
    # Добавляю сообщение в очередь сообщений.
    elif ACTION in message and message[ACTION] == MESSAGE \
            and DESTINATION in message and TIME in message \
            and SENDER in message and MESSAGE_TEXT in message:
        messages_list.append(message)
    # Клиент ожидает выхода.
    elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
        clients.remove(registered_names[message[ACCOUNT_NAME]])
        registered_names[message[ACCOUNT_NAME]].close()
        del registered_names[message[ACCOUNT_NAME]]
    # Иначе отдаём Bad request (Запрос некорректен).
    else:
        response = RESPONSE_400
        response[ERROR] = 'Запрос некорректен.'
        send_message(client, response)
        return RESPONSE_400


@Log(SERVER_LOGGER)
def process_message(message: dict, registered_names: dict, listen_socks: list):
    """ Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
    список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
    :param message: Сообщение готовое к отправке в виде словаря.
    :param registered_names: Словарь, содержащий имена зарегистрированных пользователей и их сокеты.
    :param listen_socks: Список файловых дескрипторов, готовых к выводу.
    """
    if message[DESTINATION] in registered_names \
            and registered_names[message[DESTINATION]] in listen_socks:
        try:
            send_message(registered_names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                               f'от пользователя {message[SENDER]}.')
        except NonDictInputError:
            SERVER_LOGGER.error(f'От клиента {registered_names[message[DESTINATION]].getpeername()} '
                                f'приняты некорректные данные. Соединение закрывается.')
            registered_names[message[DESTINATION]].close()
    elif message[DESTINATION] in registered_names \
            and registered_names[message[DESTINATION]] not in listen_socks:
        raise ConnectionError
    else:
        SERVER_LOGGER.error(f'Пользователь {message[DESTINATION]} не зарегистрирован'
                            f' на сервере, отправка сообщения невозможна.')


@Log(SERVER_LOGGER)
def get_arg_commandline() -> tuple:
    """ Создаём парсер аргументов коммандной строки
    и читаем параметры, возвращаем 3 параметра
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    # проверка получения корректного номера порта для работы сервера.
    if not 1023 < listen_port < 65536:
        SERVER_LOGGER.critical(f'Попытка запуска сервера с указанием неподходящего '
                               f'порта {listen_port}. Допустимы адреса с 1024 до 65535.')
        sys.exit(1)

    return listen_address, listen_port


def main():
    # Загрузка параметров командной строки,
    # если нет параметров, то задаются значения по умоланию.
    listen_address, listen_port = get_arg_commandline()
    SERVER_LOGGER.info(f'Запущен сервер, порт для подключений: {listen_port}, '
                       f'адрес с которого принимаются подключения: {listen_address}. '
                       f'Если адрес не указан, принимаются соединения с любых адресов.')
    # Подготовка сокета.
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))
    transport.settimeout(0.5)
    transport.listen(MAX_CONNECTIONS)

    clients = []  # Для клиентских клиентских сокетов.
    message_queue = []  # Для очереди сообщений.
    registered_names = {}  # Словарь, для имён пользователей и соответствующих им сокетов.

    # Основной цикл программы сервера.
    while True:
        # Жду подключения, если таймаут (0.5 сек) вышел, отлавливаю исключение OSError.
        try:
            client, client_address = transport.accept()
        except OSError as err:
            pass
        else:
            SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
            clients.append(client)

        recv_data_lst = []  # Для файловых дескрипторов готовых к вводу.
        send_data_lst = []  # Для файловых дескрипторов готовых к выводу.
        err_lst = []  # Для исключений.

        # Проверка ждущих клиентов селектом.
        try:
            if clients:
                recv_data_lst, send_data_lst, err_lst = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # Принимаю сообщения и если там есть сообщения,
        # кладу в словарь, если ошибка, исключаю клиента.
        if recv_data_lst:
            for client_with_message in recv_data_lst:
                try:
                    message_from_client = get_message(client_with_message)
                    SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message_from_client}')
                    process_client_message(message_from_client, message_queue, client_with_message,
                                           clients, registered_names)
                except json.JSONDecodeError:
                    SERVER_LOGGER.error(f'Не удалось декодировать JSON строку, полученную от '
                                        f'клиента {client_with_message.getpeername()}. '
                                        f'Соединение закрывается.')
                    client_with_message.close()
                except IncorrectDataRecivedError:
                    SERVER_LOGGER.error(f'От клиента {client_with_message.getpeername()} '
                                        f'приняты некорректные данные. Соединение закрывается.')
                    client_with_message.close()
                except Exception:
                    SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                       f'отключился от сервера.')
                    clients.remove(client_with_message)

        # Обработка каждого сообщения из очереди, если они есть.
        for message in message_queue:
            try:
                process_message(message, registered_names, send_data_lst)
            except Exception:
                SERVER_LOGGER.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                clients.remove(registered_names[message[DESTINATION]])
                del registered_names[message[DESTINATION]]
        message_queue.clear()


if __name__ == '__main__':
    main()
