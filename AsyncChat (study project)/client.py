"""Программа-клиент"""

import sys
import json
import time
import socket
import logging
import argparse
import threading
from decorators import Log
from datetime import datetime
from metaclasses import ClientMaker
from common.utils import get_message, send_message
from logs.config_client_log import create_client_logger
from exceptions import ReqFieldMissingError, ServerError, \
    IncorrectDataRecivedError, NonDictInputError
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, \
    DEFAULT_PORT, ERROR, DEFAULT_IP_ADDRESS, MESSAGE_TEXT, MESSAGE, SENDER, DESTINATION, EXIT

# Инициализация клиентского логгера.
CLIENT_LOGGER = create_client_logger()


class ClientSender(threading.Thread, metaclass=ClientMaker): # metaclass=ClientMaker
    # """ Класс формировки и отправки сообщений
    # на сервер и взаимодействия с пользователем. """
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def create_exit_message(self) -> dict:
        """ Метод формирует сообщение о выходе
        клиента и возвращает его в виде словаря.
        :return Сформированное сообщение о выходе по протоколу JIM.
        """
        time_now = datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A ")
        exit_message = {
            ACTION: EXIT,
            TIME: time_now,
            ACCOUNT_NAME: self.account_name
        }
        return exit_message

    def create_message(self) -> None:
        """ Метод запрашивает текст сообщения и имя получателя для отправки.
        Так же завершает работу при вводе подобной комманды.
        """
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        time_now = datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A ")  # текущее время
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time_now,
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
            CLIENT_LOGGER.error(f'Соединение с сервером было потеряно.')
            sys.exit(1)
        except NonDictInputError:
            CLIENT_LOGGER.error(f'От клиента {self.sock.getpeername()} '
                                f'приняты некорректные данные. Соединение закрывается.')

    def run(self):
        """Метод для взаимодействия с пользователем,
        запрашивает команды, отправляет сообщения.
        """
        self.print_help()
        while True:
            command = input('Введите команду: ').lower()
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                try:
                    exit_message = self.create_exit_message()  # Формирую сообщение о выходе.
                    send_message(self.sock, exit_message)  # Отправляю о выходе
                except NonDictInputError:
                    CLIENT_LOGGER.error(f'От клиента {self.sock.getpeername()} '
                                        f'приняты некорректные данные. Соединение закрывается.')
                print('Завершение соединения.')
                CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                time.sleep(0.5)  # Задержка, чтобы успело уйти сообщение о выходе
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def print_help(self) -> None:
        """ Функция выводящяя справку по использованию клиентской части """

        print('Поддерживаемые команды:')
        print('message - отправить сообщение.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


class ClientReader(threading.Thread, metaclass=ClientMaker):
    # """ Класс-приёмник сообщений с сервера.
    # Принимает сообщения, выводит в консоль."""
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def run(self) -> None:
        """ Метод - обработчик сообщений других
        пользователей, поступающих с сервера.
        Принимает сообщения, выводит в консоль.
        Завершается при потере соединения.
        """
        while True:  # Основной цикл приёмника сообщений.
            try:
                message = get_message(self.sock)
                if ACTION in message and message[ACTION] == MESSAGE \
                        and SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                    print(f'\nCообщение от {message[SENDER]}: "{message[MESSAGE_TEXT]}"')
                    CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                       f'\n{message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                break


@Log(CLIENT_LOGGER)
def create_presence(account_name: str = 'Guest') -> dict:
    """ Функция формирует запрос о присутствии
    клиента и возвращает его в виде словаря по протоколу JIM.
    :param account_name: Имя отправителя.
    :return Сформированное сообщение о присутствии по протоколу JIM.
    """
    time_now = datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A ")
    presence_message = {
        ACTION: PRESENCE,
        TIME: time_now,
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return presence_message


@Log(CLIENT_LOGGER)
def process_ans(message: dict) -> str:
    """ Функция разбирает ответ сервера на сообщение о присутствии,
    возращает 200 если все ОК или генерирует исключение при ошибке
    :param message: Сообщение от сервера.
    :return полученный ответ от сервера в виде строки.
    """
    CLIENT_LOGGER.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@Log(CLIENT_LOGGER)
def get_arg_commandline() -> tuple:
    """ Создаём парсер аргументов коммандной строки
    и читаем параметры, возвращаем 3 параметра
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    # проверка подходящего номера порта.
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        sys.exit(1)

    return server_address, server_port, client_name


def main():
    # Загружаем параметры командной строки и сообщаем о запуске в консоль.
    server_address, server_port, client_name = get_arg_commandline()
    print(f'Консольный месседжер. Клиентский модуль.')

    # На случай, если имя пользователя не было задано, изначально.
    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: адрес сервера: {server_address}, '
                       f'порт: {server_port}, имя пользователя: {client_name}')

    # Инициализация сокета и отправка сообщения серверу о нашем появлении.
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        message_to_server = create_presence(client_name)
        send_message(transport, message_to_server)
        CLIENT_LOGGER.debug(f'Сообщение о присутствии отправлено на сервер: {server_address}, порт: {server_port}')
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Соединение установлено. Принят ответ от сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
        sys.exit(1)
    except ServerError as error:
        CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except (ConnectionRefusedError, ConnectionError):
        CLIENT_LOGGER.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    else:
        # Запуск клиентского процесса приёма сообщений.
        module_reciver = ClientReader(client_name, transport)
        module_reciver.daemon = True
        module_reciver.start()

        # Запуск отправки сообщений и взаимодействия с пользователем.
        module_sender = ClientSender(client_name, transport)
        module_sender.daemon = True
        module_sender.start()
        CLIENT_LOGGER.debug('Запущены потоки/процессы.')

        # Завершаем все потоки.
        while True:
            time.sleep(1)
            if module_reciver.is_alive() and module_sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
