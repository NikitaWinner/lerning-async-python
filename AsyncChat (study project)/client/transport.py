import sys
import time
import hmac
import json
import socket
import hashlib
import binascii
import threading
from datetime import datetime
from Crypto.PublicKey.RSA import RsaKey
from PyQt5.QtCore import pyqtSignal, QObject
sys.path.append('../')
from common.settings import *
from common.exceptions import ServerError
from client.database import ClientDatabase
from common.utils import get_message, send_message
from logs.config_client_log import create_client_logger

# Инициализация логгера для клиента.
logger = create_client_logger()
# Объект блокировки для работы с сокетом.
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    """ Класс реализующий транспортную подсистему клиентского
    модуля. Отвечает за взаимодействие с сервером. """

    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(dict)
    message_205 = pyqtSignal()
    connection_lost = pyqtSignal()


    def __init__(self, username: str, ip_address: str, port: int, database: ClientDatabase, password: str, keys: RsaKey):
        """ Конструктор класса ClientTransport устанавливает сооединение
         с сервером и обновляет таблицы известных пользователей и контактов.
        :param username: Уникальный логин пользователя.
        :param ip_address: IP-Адрес клиента.
        :param port: Порт подключения клиента.
        :param database: Объект базы данных клиента.
        :param password: Пароль клиента при входе.
        :param keys: Объект сгенерированного ключа клиента. """
        # Вызываем конструктор предка.
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.username = username
        self.database = database
        self.password = password
        self.keys = keys
        # Сокет для работы с сервером.
        self.transport = None
        # Устанавливаем соединение с сервером.
        self.connection_init(ip_address, port)
        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                logger.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            logger.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            logger.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
        # Флаг продолжения работы транспорта.
        self.running = True

    def connection_init(self, ip_address: str, port: int) -> None:
        """ Метод отвечающий за установку соединения с сервером.
        :param ip_address: IP-Адрес клиента.
        :param port: Порт подключения клиента. """
        # Инициализация сокета.
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут необходим для освобождения сокета.
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip_address, port))
            # OSError, ConnectionRefusedError
            except (ConnectionAbortedError, ConnectionRefusedError,
                    ConnectionResetError, ConnectionError, OSError):
                pass
            else:
                connected = True
                logger.debug("Connection established.")
                break
            time.sleep(1)

        # Если соединится не удалось - исключение ServerError.
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Установлено соединение с сервером')

        # Запускаем процедуру авторизации и получаем хэш пароля.
        passwd_bytes = self.password.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        passwd_hash_string = binascii.hexlify(passwd_hash)

        logger.debug(f'Passwd hash ready: {passwd_hash_string}')

        # Получаем публичный ключ и декодируем его из байтов
        pubkey = self.keys.publickey().export_key().decode('ascii')

        # Авторизируемся на сервере
        with socket_lock:
            time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
            presense = {
                ACTION: PRESENCE,
                TIME: time_now,
                USER: {
                    ACCOUNT_NAME: self.username,
                    PUBLIC_KEY: pubkey
                }
            }
            logger.debug(f"Presense message = {presense}")
            # Отправляем серверу приветственное сообщение.
            try:
                send_message(self.transport, presense)
                answer = get_message(self.transport)
                logger.debug(f'Server response = {answer}.')
                # Если сервер вернул ошибку, бросаем исключение.
                if RESPONSE in answer:
                    if answer[RESPONSE] == 400:
                        raise ServerError(answer[ERROR])
                    elif answer[RESPONSE] == 511:
                        # Если всё нормально, то продолжаем процедуру авторизации.
                        ans_data = answer[DATA]
                        hash = hmac.new(passwd_hash_string,
                                        ans_data.encode('utf-8'), 'MD5')
                        digest = hash.digest()
                        my_ans = RESPONSE_511
                        my_ans[DATA] = binascii.b2a_base64(digest).decode('ascii')
                        send_message(self.transport, my_ans)
                        self.process_server_ans(get_message(self.transport))
            except (OSError, json.JSONDecodeError) as err:
                logger.debug(f'Connection error.', exc_info=err)
                raise ServerError('Сбой соединения в процессе авторизации.')
    def create_presence(self) -> dict:
        """ Метод, генерирующий приветственное сообщение серверу
        о присутствии клиента и возвращает его в виде словаря по протоколу JIM.
        :return presence_message: Сообщение о присутствии по протоколу JIM. """
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        presence_message = {
            ACTION: PRESENCE,
            TIME: time_now,
            USER: {
                ACCOUNT_NAME: self.username
            }
        }
        logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.username}')
        return presence_message

    def process_server_ans(self, message: dict) -> None:
        """ Метод, обрабатывает поступающие ответы сервера.
        Генерирует исключение при ошибке.
        :param message: Сообщение от сервера.
        :return: Полученный код от сервера в виде строки. """
        logger.debug(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.user_list_update()
                self.contacts_list_update()
                self.message_205.emit()
            else:
                logger.error(
                    f'Принят неизвестный код подтверждения {message[RESPONSE]}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        elif ACTION in message \
                and SENDER in message \
                and DESTINATION in message \
                and MESSAGE_TEXT in message \
                and message[ACTION] == MESSAGE \
                and message[DESTINATION] == self.username:
            logger.debug(f'Получено сообщение от пользователя {message[SENDER]}:'
                         f'{message[MESSAGE_TEXT]}')
            self.new_message.emit(message)

    def contacts_list_update(self) -> None:
        """ Метод, обновляющий контакт - лист с сервера"""
        logger.debug(f'Запрос контакт листа для пользователя {self.name}')
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        request = {
            ACTION: GET_CONTACTS,
            TIME: time_now,
            USER: self.username
        }
        logger.debug(f'Сформирован запрос {request}')
        with socket_lock:
            send_message(self.transport, request)
            answer = get_message(self.transport)
        logger.debug(f'Получен ответ {answer}')
        if RESPONSE in answer and answer[RESPONSE] == 202:
            for contact in answer[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            logger.error('Не удалось обновить список контактов.')

    def user_list_update(self) -> None:
        """ Метод обновления таблицы известных пользователей. """
        logger.debug(f'Запрос списка известных пользователей {self.username}')
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        request = {
            ACTION: USERS_REQUEST,
            TIME: time_now,
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            send_message(self.transport, request)
            answer = get_message(self.transport)
        if RESPONSE in answer and answer[RESPONSE] == 202:
            self.database.add_users(answer[LIST_INFO])
        else:
            logger.error('Не удалось обновить список известных пользователей.')

    def key_request(self, username: str) -> str:
        """ Метод запрашивающий с сервера публичный ключ пользователя.
        :param username: Уникальный логин пользователя.
        :return: Публичный ключ из базы данных сервера. """
        logger.debug(f'Запрос публичного ключа для {username}')
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        request = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time_now,
            ACCOUNT_NAME: username
        }
        with socket_lock:
            send_message(self.transport, request)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 511:
            return ans[DATA]
        else:
            logger.error(f'Не удалось получить ключ собеседника{username}.')
    def add_contact(self, new_contact: str) -> None:
        """ Метод сообщающий на сервер о добавлении нового контакта
        :param new_contact: Уникальный логин нового контакта. """
        logger.debug(f'Создание контакта {new_contact}')
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        request = {
            ACTION: ADD_CONTACT,
            TIME: time_now,
            USER: self.username,
            ACCOUNT_NAME: new_contact
        }
        with socket_lock:
            send_message(self.transport, request)
            answer = get_message(self.transport)
            self.process_server_ans(answer)

    def remove_contact(self, old_contact: str) -> None:
        """ Метод удаления клиента на сервере
        :param old_contact: Уникальный логин старого контакта.
        """
        logger.debug(f'Удаление контакта {old_contact}')
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        request = {
            ACTION: REMOVE_CONTACT,
            TIME: time_now,
            USER: self.username,
            ACCOUNT_NAME: old_contact
        }
        with socket_lock:
            send_message(self.transport, request)
            answer = get_message(self.transport)
            self.process_server_ans(answer)

    def transport_shutdown(self) -> None:
        """Метод закрытия соединения, отправляет серверу сообщение о выходе. """
        self.running = False
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        message = {
            ACTION: EXIT,
            TIME: time_now,
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        logger.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    def send_message(self, to: str, message: str) -> None:
        """ Метод отправки на сервер сообщения для другого пользователя.
        :param to: Уникальный логин получателя.
        :param message: Текст отправляемого сообщения. """
        time_now = datetime.now().strftime("%A | %H:%M:%S |%d %B %Yг ")
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time_now,
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            send_message(self.transport, message_dict)
            answer = get_message(self.transport)
            self.process_server_ans(answer)
            logger.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        """ Метод содержащий основной цикл работы транспортного потока. """
        logger.debug('Запущен процесс - приёмник сообщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет. Если не сделать тут задержку,
            # то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            message = None
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        # выход по таймауту вернёт номер ошибки err.errno равный None
                        # поэтому, при выходе по таймауту мы сюда попросту не попадём
                        logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError,
                        TypeError, ConnectionRefusedError):
                    logger.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                finally:
                    self.transport.settimeout(5)
            # Если сообщение получено, то вызываем функцию обработчик:
            if message:
                logger.debug(f'Принято сообщение с сервера: {message}')
                self.process_server_ans(message)

