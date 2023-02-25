"""Программа-сервер"""

import os
import sys
import json
import select
import socket
import argparse
import threading
import configparser
from decorators import Log
from descriptors import Port
from PyQt5.QtCore import QTimer
from metaclasses import ServerMaker
from server_database import ServerStorage
from common.utils import get_message, send_message
from PyQt5.QtWidgets import QApplication, QMessageBox
from logs.config_server_log import create_server_logger
from exceptions import IncorrectDataRecivedError, NonDictInputError
from server_gui import MainWindow, gui_create_model, HistoryWindow, \
    create_stat_model, ConfigWindow
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    SENDER, GET_CONTACTS, MAX_CONNECTIONS, ERROR, MESSAGE_TEXT, MESSAGE, \
    RESPONSE_200, RESPONSE_202, RESPONSE_400, DESTINATION, USERS_REQUEST, \
    EXIT, LIST_INFO, ADD_CONTACT, REMOVE_CONTACT

# from PyQt5.QtGui import QStandardItemModel, QStandardItem

# Инициализация логгера для сервера.
SERVER_LOGGER = create_server_logger()

# Флаг, что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()


class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()  # Дескриптор для описания порта.
    """ Основной класс сервера """

    def __init__(self, listen_address: str, listen_port: int, database: ServerStorage):
        self.addr = listen_address  # IP-адрес.
        self.port = listen_port  # Порты для прослушивания.
        self.database = database  # База данных сервера.
        self.clients = list()  # Для подключенных клиентских сокетов.
        self.message_queue = list()  # Для очереди сообщений.
        self.registered_names = dict()  # Словарь, для имён пользователей и соответствующих им сокетов.
        super().__init__()  # Конструктор предка

    def init_socket(self):
        """ Метод для создания и настройки сокета сервера"""
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовлю и слушаю сокет.
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)
        self.sock = transport
        self.sock.listen(MAX_CONNECTIONS)

    def run(self):
        """ Основной цикл программы сервера."""
        # Инициализация cокета.
        self.init_socket()
        while True:
            # Ждём подключения, если таймаут (0.5 сек) вышел, отлавливаю исключение OSError.
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
                if self.clients:  # Проверка на наличие ждущих клиентов.
                    recv_data_lst, send_data_lst, err_lst = select.select(
                        self.clients, self.clients, [], 0)
            except OSError as err:
                SERVER_LOGGER.error(f'Ошибка работы с сокетами: {err}')
            # Принимаю сообщения и если там есть сообщения,
            # кладу в словарь, если ловлю ошибку, исключаю клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        message_from_client = get_message(client_with_message)
                        SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message_from_client}')
                        self.process_client_message(message_from_client, client_with_message)
                    except OSError:
                        # Ищем клиента в словаре клиентов и удаляем его из него
                        # и базы подключённых
                        SERVER_LOGGER.info(
                            f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        for name in self.registered_names:
                            if self.registered_names[name] == client_with_message:
                                self.database.user_logout(name)
                                del self.registered_names[name]
                                break
                        self.clients.remove(client_with_message)
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
                except (ConnectionAbortedError, ConnectionError,
                        ConnectionResetError, ConnectionRefusedError) as err:
                    SERVER_LOGGER.info(f'Связь с клиентом с именем '
                                       f'{message[DESTINATION]} была потеряна, '
                                       f' ошибка {err}')
                    self.clients.remove(self.registered_names[message[DESTINATION]])
                    self.database.user_logout(message[DESTINATION])
                    del self.registered_names[message[DESTINATION]]
            self.message_queue.clear()

    def process_message(self, message: dict, listen_socks: list) -> None:
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

    def process_client_message(self, message: dict, client: socket.socket) -> None:
        """ Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет корректность, отправляет клиенту словарь-ответ, если необходимо.
        :param message: Сообщение в виде словаря принятое от клиента по протоколу JIM.
        :param client: Файловый дескриптор, готовый к вводу (готовый принять сообщение от сервера).
        """
        global new_connection
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
                ip_address, port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME],
                                         str(ip_address), int(port))
                send_message(client, RESPONSE_200)
                SERVER_LOGGER.debug(f'Ответ отправлен клиенту : {RESPONSE_200}')
                with conflag_lock:
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                SERVER_LOGGER.debug(f'Ответ отправлен клиенту : {response}')
                self.clients.remove(client)
                client.close()
        # Добавляю сообщение в очередь сообщений.
        elif ACTION in message \
                and message[ACTION] == MESSAGE \
                and DESTINATION in message \
                and TIME in message \
                and SENDER in message \
                and MESSAGE_TEXT in message \
                and self.registered_names[message[SENDER]] == client:
            self.message_queue.append(message)
            self.database.process_message(message[SENDER],
                                          message[DESTINATION])
        # Клиент ожидает выхода.
        elif ACTION in message \
                and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message \
                and self.registered_names[message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            SERVER_LOGGER.info(f'Клиент {message[ACCOUNT_NAME]} '
                               f'корректно отключился от сервера.')
            self.clients.remove(self.registered_names[message[ACCOUNT_NAME]])
            self.registered_names[message[ACCOUNT_NAME]].close()
            # Удаляем из доступных пользователей
            del self.registered_names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
        # Если это запрос контакт-листа
        elif ACTION in message \
                and message[ACTION] == GET_CONTACTS \
                and USER in message \
                and self.registered_names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)

        # Если это добавление контакта
        elif ACTION in message \
                and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.registered_names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это удаление контакта
        elif ACTION in message \
                and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.registered_names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это запрос известных пользователей
        elif ACTION in message \
                and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.registered_names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            all_user_list = [user[0] for user in self.database.get_users_list()]
            response[LIST_INFO] = all_user_list
            send_message(client, response)
        # Иначе отдаём Bad request (Запрос некорректен).
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            SERVER_LOGGER.error(f'Ответ отправлен клиенту : {response}')


def print_help() -> None:
    """ Функция выводящая справку по использованию серверной части """

    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


@Log(SERVER_LOGGER)
def get_arg_commandline(default_port: str, default_address: str) -> tuple:
    """ Создаём парсер аргументов коммандной строки
    и читаем параметры, возвращаем 2 параметра.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port


def main():
    # Загрузка файла конфигурации сервера
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server_config.ini'}")

    # Инициализация базы данных
    path_to_database = os.path.join(config['SETTINGS']['Database_path'],
                                    config['SETTINGS']['Database_file'])
    database = ServerStorage(path_to_database)

    # Загрузка параметров командной строки, если нет параметров,
    # то задаются значения по умоланию из файла конфигурации.
    listen_address, listen_port = get_arg_commandline(config['SETTINGS']['Default_port'],
                                                      config['SETTINGS']['Listen_Address'])
    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Создаём графическое окружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    def list_update() -> None:
        """ Функция, обновляющая список подключённых,
        проверяет флаг подключения, и если надо, обновляет список.
        """
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    def show_statistics() -> None:
        """ Функция, создающая окно со статистикой клиентов. """

        global statistics_window
        statistics_window = HistoryWindow()
        statistics_window.history_table.setModel(create_stat_model(database))
        statistics_window.history_table.resizeColumnsToContents()
        statistics_window.history_table.resizeRowsToContents()
        statistics_window.show()

    def server_config():
        """ Функция создающая окно с настройками сервера. """

        global config_window
        # Создаём окно настройки сервера и заносим
        # в него параметры из файла конфигурации.
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    def save_server_config():
        """ Функция сохранения настроек. """
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть целым числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()
