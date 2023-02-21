"""Программа-сервер"""

import sys
import json
import socket
import select
import logging
import argparse
from decorators import Log
from descriptors import Port
from logs.config_server_log import create_server_logger
from metaclasses import ServerMaker
from common.utils import get_message, send_message
from exceptions import IncorrectDataRecivedError, NonDictInputError
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    SENDER, DEFAULT_PORT, MAX_CONNECTIONS, ERROR, MESSAGE_TEXT, MESSAGE, \
    RESPONSE_200, RESPONSE_400, DESTINATION, EXIT

# Инициализация логирования сервера.
SERVER_LOGGER = create_server_logger()


class Server(metaclass=ServerMaker): # metaclass=ServerMaker
    port = Port()
    """ Основной класс сервера """
    def __init__(self, listen_address, listen_port):
        self.addr = listen_address  # IP-адрес.
        self.port = listen_port  # Порты для прослушивания.
        self.clients = []  # Для подключенных клиентских сокетов.
        self.message_queue = []  # Для очереди сообщений.
        self.registered_names = dict()  # Словарь, для имён пользователей и соответствующих им сокетов.

    def init_socket(self):
        """ Метод для создания подготовки и настройки сокета сервера"""
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовлю и слушаю сокет.
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)
        self.sock = transport
        self.sock.listen(MAX_CONNECTIONS)

    def main_loop(self):
        """ Основной цикл программы сервера."""

        self.init_socket()  # Инициализация cокета.
        while True:
            # Жду подключения, если таймаут (0.5 сек) вышел, отлавливаю исключение OSError.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)
            recv_data_lst = []  # Для файловых дескрипторов готовых к вводу.
            send_data_lst = []  # Для файловых дескрипторов готовых к выводу.
            err_lst = []  # Для исключений.
            try:
                if self.clients:  # Проверка наличия ждущих клиентов.
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass
            # Принимаю сообщения и если там есть сообщения,
            # кладу в словарь, если ловлю ошибку, исключаю клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        message_from_client = get_message(client_with_message)
                        SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message_from_client}')
                        self.process_client_message(message_from_client, client_with_message)
                    except json.JSONDecodeError:
                        SERVER_LOGGER.error(f'Не удалось декодировать JSON строку, полученную от '
                                            f'клиента {client_with_message.getpeername()}. '
                                            f'Соединение закрывается.')
                        client_with_message.close()
                    except (IncorrectDataRecivedError, NonDictInputError):
                        SERVER_LOGGER.error(f'От клиента {client_with_message.getpeername()} '
                                            f'приняты некорректные данные. Соединение закрывается.')
                        client_with_message.close()
                    except Exception as err:
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                           f'отключился от сервера. Ошибка: {err}')
                        self.clients.remove(client_with_message)

            # Обработка каждого сообщения из очереди, если они есть.
            for message in self.message_queue:
                try:
                    self.process_message(message, send_data_lst)
                except Exception as e:
                    SERVER_LOGGER.info(f'Связь с клиентом с именем '
                                       f'{message[DESTINATION]} была потеряна, '
                                       f' ошибка {e}')
                    self.clients.remove(self.registered_names[message[DESTINATION]])
                    del self.registered_names[message[DESTINATION]]
            self.message_queue.clear()

    def process_message(self, message: dict, listen_socks: list):
        """ Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        :param message: Сообщение готовое к отправке в виде словаря.
        :param listen_socks: Список файловых дескрипторов, готовых к выводу.
        """
        if message[DESTINATION] in self.registered_names \
                and self.registered_names[message[DESTINATION]] in listen_socks:
            try:
                send_message(self.registered_names[message[DESTINATION]], message)
                SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                                   f'от пользователя {message[SENDER]}.')
            except NonDictInputError:
                SERVER_LOGGER.error(f'От клиента {self.registered_names[message[DESTINATION]].getpeername()} '
                                    f'приняты некорректные данные. Соединение закрывается.')
                self.registered_names[message[DESTINATION]].close()
        elif message[DESTINATION] in self.registered_names \
                and self.registered_names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(f'Пользователь {message[DESTINATION]} не зарегистрирован'
                                f' на сервере, отправка сообщения невозможна.')

    def process_client_message(self, message: dict, client: socket.socket):
        """ Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет корректность, отправляет клиенту словарь-ответ, если необходимо.
        :param message: Сообщение в виде словаря принятое от клиента по протоколу JIM.
        :param client: Файловый дескриптор, готовый к вводу (готовый принять сообщение от сервера).
        """
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Принимаем и отвечаем на собщение о присутствии.
        if ACTION in message \
                and message[ACTION] == PRESENCE \
                and TIME in message \
                and USER in message:
            # Если такой пользователь ещё не зарегистрирован,
            # регистрирую, иначе отправляю ответ 400 и завершаю соединение.
            if message[USER][ACCOUNT_NAME] not in self.registered_names.keys():
                self.registered_names[message[USER][ACCOUNT_NAME]] = client  # {'client_name': client_socket}
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
        # Добавляю сообщение в очередь сообщений.
        elif ACTION in message \
                and message[ACTION] == MESSAGE \
                and DESTINATION in message \
                and TIME in message \
                and SENDER in message \
                and MESSAGE_TEXT in message:
            self.message_queue.append(message)
        # Клиент ожидает выхода.
        elif ACTION in message \
                and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message:
            self.clients.remove(self.registered_names[message[ACCOUNT_NAME]])
            self.registered_names[message[ACCOUNT_NAME]].close()
            del self.registered_names[message[ACCOUNT_NAME]]
        # Иначе отдаём Bad request (Запрос некорректен).
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)


@Log(SERVER_LOGGER)
def get_arg_commandline() -> tuple:
    """ Создаём парсер аргументов коммандной строки
    и читаем параметры, возвращаем 2 параметра.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port


def main():
    # Загрузка параметров командной строки,
    # если нет параметров, то задаются значения по умоланию.
    listen_address, listen_port = get_arg_commandline()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port)
    server.main_loop()


if __name__ == '__main__':
    main()
