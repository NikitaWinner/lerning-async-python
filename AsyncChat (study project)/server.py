"""Программа-сервер"""

import socket
import sys
import argparse
import json
import logging
import select
from datetime import datetime
import logs.config_server_log
from exceptions import IncorrectDataRecivedError, NonDictInputError
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, DEFAULT_PORT, MAX_CONNECTIONS, ERROR, MESSAGE_TEXT, MESSAGE, SENDER
from common.utils import get_message, send_message
from decorators import Log


# Инициализация логирования сервера.
SERVER_LOGGER = logging.getLogger('server')
TIME_IS_NOW = datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A ")


@Log(SERVER_LOGGER)
def process_client_message(message: dict, messages_list: list, client) -> dict|None:
    """ Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
    проверяет корректность, отправляет словарь-ответ для клиента с результатом приёма. """

    SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {message}')

    # Если это сообщение о присутствии, принимаем и отвечаем, если успех
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
        response = {RESPONSE: 200}
        SERVER_LOGGER.info(f'Cформирован ответ клиенту {response}')
        send_message(client, response)
        return response

    # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
    elif ACTION in message and message[ACTION] == MESSAGE and \
            TIME in message and MESSAGE_TEXT in message:
        messages_list.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT]))

    # Иначе отдаём Bad request
    else:
        response = {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }
        SERVER_LOGGER.info(f'Cформирован ответ клиенту {response}')
        send_message(client, response)
        return response


@Log(SERVER_LOGGER)
def get_arg_commandline():
    """Парсер аргументов командной строки"""

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    # проверка получения корректного номера порта для работы сервера.
    if not 1023 < listen_port < 65536:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с указанием неподходящего порта '
            f'{listen_port}. Допустимы адреса с 1024 до 65535.')
        sys.exit(1)

    return listen_address, listen_port

def main():
    """ Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию """

    listen_address, listen_port = get_arg_commandline()
    SERVER_LOGGER.info(f'Запущен сервер, порт для подключений: {listen_port}, '
                       f'адрес с которого принимаются подключения: {listen_address}. '
                       f'Если адрес не указан, принимаются соединения с любых адресов.')

    # Готовим сокет
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.bind((listen_address, listen_port))
    transport.settimeout(0.5)

    # список клиентов , очередь сообщений
    clients = []
    message_queue = []

    # Слушаем порт
    transport.listen(MAX_CONNECTIONS)

    # Основной цикл программы сервера
    while True:
        # Ждём подключения, если таймаут вышел, ловим исключение.
        try:
            client, client_address = transport.accept()
        except OSError as err:
            print(err.errno)
            pass
        else:
            SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
            clients.append(client)
        recv_data_lst = []
        send_data_lst = []
        err_lst = []

        # Проверяем на наличие ждущих клиентов через select
        try:
            if clients:
                recv_data_lst, send_data_lst, err_lst = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # принимаем сообщения и если там есть сообщения,
        # кладём в словарь, если ошибка, исключаем клиента.
        if recv_data_lst:
            for client_with_message in recv_data_lst:
                try:
                    message_from_client = get_message(client_with_message)
                    SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message_from_client}')
                    process_client_message(message_from_client, message_queue, client_with_message)
                except json.JSONDecodeError:
                    SERVER_LOGGER.error(f'Не удалось декодировать JSON строку, полученную от '
                                        f'клиента {client_with_message.getpeername()}. Соединение закрывается.')
                    client_with_message.close()

                except IncorrectDataRecivedError:
                    SERVER_LOGGER.error(f'От клиента {client_with_message.getpeername()} приняты некорректные данные. '
                                        f'Соединение закрывается.')
                    client_with_message.close()

                except:
                    SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                       f'отключился от сервера.')
                    clients.remove(client_with_message)

        # Если есть сообщения для отправки и ожидающие клиенты, отправляем им сообщение.
        if message_queue and send_data_lst:
            message = {
                ACTION: MESSAGE,
                SENDER: message_queue[0][0],
                TIME: datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A "),
                MESSAGE_TEXT: message_queue[0][1]
            }
            del message_queue[0]
            for waiting_client in send_data_lst:
                try:
                    send_message(waiting_client, message)
                except NonDictInputError:
                    SERVER_LOGGER.error(f'От клиента {waiting_client.getpeername()} приняты некорректные данные. '
                                        f'Соединение закрывается.')
                    waiting_client.close()
                except:
                    SERVER_LOGGER.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                    waiting_client.close()
                    clients.remove(waiting_client)

if __name__ == '__main__':
    main()
