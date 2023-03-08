import os
import sys
import json
import hmac
import select
import socket
import binascii
import threading

sys.path.append('../')
from server.database import ServerStorage
from common.settings import *
from common.descriptors import Port
from common.decorators import LoginRequired
from common.utils import send_message, get_message
from logs.config_server_log import create_server_logger
from common.exceptions import IncorrectDataRecivedError, NonDictInputError

# Загрузка логгера.
logger = create_server_logger()


class MessageProcessor(threading.Thread):
    # """
    # Основной класс сервера. Принимает соединения, словари - пакеты
    # от клиентов, обрабатывает поступающие сообщения.
    # Работает в качестве отдельного потока.
    # """
    port = Port()

    def __init__(self, listen_address: str, listen_port: int, database: ServerStorage):
        """
        :param listen_address: IP-адрес для прослушивания.
        :param listen_port: Порты для прослушивания.
        :param database: Объект базы данных сервера.
        """
        # Вызываем конструкторы предков
        threading.Thread.__init__(self)
        # Параметры подключения
        self.addr = listen_address
        self.port = listen_port
        self.database = database
        # Сокет, через который будет осуществляться работа
        self.sock = None
        # Сокеты
        self.listen_sockets = None
        self.error_sockets = None
        # Флаг продолжения работы основного цикла.
        self.running = True
        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()
        # Список подключённых клиентов.
        self.clients = list()

    def run(self):
        """ Основной цикл программы сервера. """
        # Инициализация Сокета.
        self.init_socket()

        # Основной цикл программы сервера.
        while self.running:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError as er:
                pass
            else:
                logger.info(f'Установлено соединение с ПК {client_address}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []
            # send_data_lst = []
            # err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = select.select(
                        self.clients, self.clients, [], 0)
            except OSError as err:
                logger.error(f'Ошибка работы с сокетами: {err.errno}')

            # Принимаем сообщения и если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        message_from_client = get_message(client_with_message)
                        logger.debug(f'Получено сообщение от клиента: {message_from_client}')
                        self.process_client_message(message_from_client, client_with_message)
                    except (OSError, json.JSONDecodeError, TypeError,
                            IncorrectDataRecivedError, NonDictInputError) as err:
                        logger.debug(f'Getting data from client exception.', exc_info=err)
                        self.remove_client(client_with_message)

    def remove_client(self, client: socket.socket) -> None:
        """ Метод-обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы. """
        logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            # Ищем клиента в словаре клиентов.
            if self.names[name] == client:
                # удаляем его из него и базы подключённых.
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def init_socket(self) -> None:
        """ Метод-инициализатор сокета. """
        logger.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.addr, self.port))
        self.sock.settimeout(0.5)
        self.sock.listen(MAX_CONNECTIONS)

    def process_message(self, message: dict) -> None:
        """ Метод адресной отправки сообщения клиенту.
        Принимает словарь-сообщение.
        :param message: Сообщение готовое к отправке в виде словаря. """
        if message[DESTINATION] in self.names \
                and self.names[message[DESTINATION]] in self.listen_sockets:
            try:
                send_message(self.names[message[DESTINATION]], message)
                logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                            f'от пользователя {message[SENDER]}.')
            except (OSError, NonDictInputError):
                logger.error(f'От клиента {self.names[message[DESTINATION]].getpeername()} '
                             f'приняты некорректные данные. Соединение закрывается.')
                self.remove_client(message[DESTINATION])
        elif message[DESTINATION] in self.names \
                and self.names[message[DESTINATION]] not in self.listen_sockets:
            logger.error(
                f'Связь с клиентом {message[DESTINATION]} была потеряна. Соединение закрыто, доставка невозможна.')
            self.remove_client(self.names[message[DESTINATION]])
        else:
            logger.error(f'Пользователь {message[DESTINATION]} не зарегистрирован'
                                f' на сервере, отправка сообщения невозможна.')

    @LoginRequired()
    def process_client_message(self, message: dict, client: socket.socket) -> None:
        """ Метод-обработчик поступающих сообщений от клиентов,
        принимает словарь-сообщение от клиента, проверяет корректность,
        отправляет клиенту словарь-ответ, если необходимо.
        :param message: Сообщение от клиента по протоколу JIM.
        :param client: Файловый дескриптор, готовый к вводу (готовый принять сообщение от сервера). """
        logger.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message \
                and message[ACTION] == PRESENCE \
                and TIME in message \
                and USER in message:
            # Если сообщение о присутствии, то вызываем функцию авторизации.
            self.user_authorization(message, client)

        # Если это сообщение, то отправляем его получателю.
        elif ACTION in message \
                and message[ACTION] == MESSAGE \
                and DESTINATION in message \
                and TIME in message \
                and SENDER in message \
                and MESSAGE_TEXT in message \
                and self.names[message[SENDER]] == client:
            if message[DESTINATION] in self.names:
                self.database.process_message(message[SENDER],
                                              message[DESTINATION])
                self.process_message(message)
                try:
                    send_message(client, RESPONSE_200)
                except (OSError, NonDictInputError):
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    send_message(client, response)
                except (OSError, NonDictInputError):
                    pass
            return

        # Если клиент выходит
        elif ACTION in message \
                and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.remove_client(client)

        # Если это запрос контакт-листа
        elif ACTION in message \
                and message[ACTION] == GET_CONTACTS \
                and USER in message \
                and self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            try:
                send_message(client, response)
            except (OSError, NonDictInputError):
                self.remove_client(client)

        # Если это добавление контакта
        elif ACTION in message \
                and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER],
                                      message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except (OSError, NonDictInputError):
                self.remove_client(client)

        # Если это удаление контакта
        elif ACTION in message \
                and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER],
                                         message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except (OSError, NonDictInputError):
                self.remove_client(client)

        # Если это запрос известных пользователей
        elif ACTION in message \
                and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            all_username_list = [user[0] for user in self.database.get_users_list()]
            response[LIST_INFO] = all_username_list
            try:
                send_message(client, response)
            except (OSError, NonDictInputError):
                self.remove_client(client)

        # Если это запрос публичного ключа пользователя
        elif ACTION in message \
                and message[ACTION] == PUBLIC_KEY_REQUEST \
                and ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            # может быть, что ключа ещё нет (пользователь никогда не логинился, тогда шлём 400)
            if response[DATA]:
                try:
                    send_message(client, response)
                except (OSError, NonDictInputError):
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Нет публичного ключа для данного пользователя'
                try:
                    send_message(client, response)
                except (OSError, NonDictInputError):
                    self.remove_client(client)

        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            try:
                send_message(client, response)
            except (OSError, NonDictInputError):
                self.remove_client(client)

    def user_authorization(self, message: dict, sock: socket.socket) -> None:
        """ Метод реализующий авторизацию пользователей.
        :param message: Сообщение от клиента.
        :param sock: Клиентский сокет. """
        # Если имя пользователя уже занято, то возвращаем 400
        logger.debug(f'Start auth process for {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            try:
                logger.debug(f'Username busy, sending {response}')
                send_message(sock, response)
            except OSError:
                logger.debug('OS Error')
                pass
            self.clients.remove(sock)
            sock.close()
        # Проверяем что пользователь зарегистрирован на сервере.
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован.'
            try:
                logger.debug(f'Unknown username, sending {response}')
                send_message(sock, response)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            logger.debug('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            message_auth = RESPONSE_511
            # Получаем набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[DATA] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем серверную версию ключа
            password_hash_bytes = self.database.get_hash(message[USER][ACCOUNT_NAME])
            hash = hmac.new(password_hash_bytes, random_str, 'MD5')
            digest = hash.digest()
            logger.debug(f'Auth message = {message_auth}')
            try:
                # Обмен с клиентом
                send_message(sock, message_auth)
                answer = get_message(sock)
            except OSError as err:
                logger.debug('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(answer[DATA])
            # Если ответ клиента корректный, то сохраняем его в список пользователей.
            if RESPONSE in answer \
                    and answer[RESPONSE] == 511 \
                    and hmac.compare_digest(digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                # добавляем пользователя в список активных и,
                # если у него изменился открытый ключ, то сохраняем новый
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль.'
                try:
                    send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self) -> None:
        """ Метод реализующий отправки сервисного сообщения 205 клиентам. """
        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])
