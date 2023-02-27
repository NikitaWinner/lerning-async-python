import sys
import time
import socket
import threading
from datetime import datetime
# from database import ClientDatabase
from PyQt5.QtCore import pyqtSignal, QObject
sys.path.append('../')
from common.utils import *
from common.settings import *
from common.exceptions import ServerError
from logs.config_client_log import create_client_logger
from client.database import ClientDatabase

# Инициализация логгера для клиента.
logger = create_client_logger()
# Объект блокировки для работы с сокетом.
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    """ Класс - Транспорт, отвечает за взаимодействие с сервером. """

    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, username: str, ip_address: str, port: int, database: ClientDatabase):
        """ Конструктор класса ClientTransport устанавливает сооединение
         с сервером и обновляет таблицы известных пользователей и контактов.
        :param username: Уникальный логин пользователя.
        :param ip_address: IP-Адрес клиента.
        :param port: Порт подключения клиента.
        :param database: Объект базы данных клиента. """
        # Вызываем конструктор предка.
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.username = username
        self.database = database
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
        """ Метод инициализации соединения с сервером
        и отправки сообщения о нашем появлении.
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
                break
            time.sleep(1)

        # Если соединится не удалось - исключение ServerError.
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Установлено соединение с сервером')

        # Посылаем серверу приветственное сообщение и получаем ответ,
        # что всё нормально или ловим исключение.
        try:
            with socket_lock:
                send_message(self.transport, self.create_presence())
                self.process_server_ans(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # Если всё хорошо, сообщение об установке соединения.
        logger.info('Соединение с сервером успешно установлено.')


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

    # Функция, обрабатывающая сообщения от сервера. Ничего не возвращает.
    # Генерирует исключение при ошибке.
    def process_server_ans(self, message: dict) -> None:
        """ Метод, обрабатывает ответ сервера. Генерирует исключение при ошибке.
        :param message: Сообщение от сервера.
        :return: Полученный код от сервера в виде строки. """
        logger.debug(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            else:
                logger.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        elif ACTION in message \
                and SENDER in message \
                and DESTINATION in message \
                and MESSAGE_TEXT in message \
                and message[ACTION] == MESSAGE \
                and message[DESTINATION] == self.username:
            logger.debug(f'Получено сообщение от пользователя {message[SENDER]}:'
                         f'{message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])

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
        """Метод закрытия соединения, отправляет сообщение о выходе. """
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
        """ Метод отправки сообщения на сервер
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
            self.process_server_ans(get_message(self.transport))
            logger.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        logger.debug('Запущен процесс - приёмник сообщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет. Если не сделать тут задержку,
            # то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    answer = get_message(self.transport)
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
                # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    logger.debug(f'Принято сообщение с сервера: {answer}')
                    self.process_server_ans(answer)
                finally:
                    self.transport.settimeout(5)
