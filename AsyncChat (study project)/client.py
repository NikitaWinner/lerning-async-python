"""Программа-клиент"""

import sys
import json
import socket
import datetime
import argparse
import logging
import logs.config_client_log
from exceptions import ReqFieldMissingError
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, DEFAULT_PORT, ERROR, DEFAULT_IP_ADDRESS
from common.utils import get_message, send_message
from decorators import Log

# Инициализация клиентского логера
CLIENT_LOGGER = logging.getLogger('client')
TIME_IS_NOW = datetime.datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A ")


@Log(CLIENT_LOGGER)
def create_presence(account_name: str = 'Guest') -> dict:
    """ Функция генерирует запрос о присутствии клиента """

    out = {
        ACTION: PRESENCE,
        TIME: TIME_IS_NOW,
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return out


@Log(CLIENT_LOGGER)
def process_ans(message):
    """ Функция разбирает ответ сервера """

    CLIENT_LOGGER.debug(f'Полученно сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        CLIENT_LOGGER.warning(f'Ответ сервера "400".')
        return f'400 : {message[ERROR]}'
    raise ReqFieldMissingError(RESPONSE)


@Log(CLIENT_LOGGER)
def create_arg_parser():
    """ Создаём парсер аргументов командной строки """

    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    return parser


def main():
    """ Загружаем параметры командной строки """

    parser = create_arg_parser()
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}.'
            f' Допустимые адреса с 1024 до 65535. Клиент завершает работу.')
        sys.exit(1)

    CLIENT_LOGGER.info(f'Запущен клиент с парамертами: '
                       f'адрес сервера: {server_address}, порт: {server_port}')
    # Инициализация сокета и обмен

    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        message_to_server = create_presence()
        send_message(transport, message_to_server)
        CLIENT_LOGGER.debug(f'Сообщение отправлено на сервер: {server_address}, порт: {server_port}')
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Принят ответ от сервера: {answer}')
        print(answer)
    except json.JSONDecodeError:
        CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
    except ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
    except ConnectionRefusedError:
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}, '
                               f'конечный компьютер отверг запрос на подключение.')


if __name__ == '__main__':
    main()
