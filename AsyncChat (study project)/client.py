"""Программа-клиент"""

import sys
import json
import time
import socket
import argparse
import threading
from decorators import Log
from datetime import datetime
from metaclasses import ClientMaker
from client_database import ClientDatabase
from common.utils import get_message, send_message
from logs.config_client_log import create_client_logger
from exceptions import ReqFieldMissingError, ServerError, \
    IncorrectDataRecivedError, NonDictInputError
from common.settings import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, \
    DEFAULT_PORT, ERROR, DEFAULT_IP_ADDRESS, MESSAGE_TEXT, MESSAGE, SENDER, EXIT, \
    GET_CONTACTS, DESTINATION, LIST_INFO, ADD_CONTACT, USERS_REQUEST, REMOVE_CONTACT

# Инициализация клиентского логгера.
CLIENT_LOGGER = create_client_logger()

# Объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


class ClientSender(threading.Thread, metaclass=ClientMaker):
    # """ Класс формировки и отправки сообщений
    # на сервер и взаимодействия с пользователем."""

    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
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
        # Проверим, что получатель существует
        with database_lock:
            if not self.database.check_user(to_user):
                CLIENT_LOGGER.error(f'Попытка отправить сообщение '
                                    f'незарегистрированому получателю: {to_user}')
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time_now,
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        # Сохраняем сообщения для истории
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
            except OSError as err:
                if err.errno:
                    CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    CLIENT_LOGGER.error('Не удалось передать сообщение. Таймаут соединения')
            except (ConnectionResetError, ConnectionError,
                    ConnectionAbortedError, ConnectionRefusedError):
                CLIENT_LOGGER.error(f'Соединение с сервером было потеряно.')
                sys.exit(1)
            except NonDictInputError:
                CLIENT_LOGGER.error(f'От клиента {self.sock.getpeername()} '
                                    f'приняты некорректные данные. Соединение закрывается.')
                self.sock.close()

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
                with sock_lock:
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
                # Список контактов
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)
            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts()
            # история сообщений.
            elif command == 'history':
                self.print_history()
            else:
                print('Команда не распознана, попробойте снова. '
                      'help - вывести поддерживаемые команды.')

    def print_help(self) -> None:
        """ Метод выводящий справку по использованию клиентской части. """

        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    def print_history(self) -> None:
        """ Метод выводящий историю сообщений"""

        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} '
                          f'от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} '
                          f'от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]},'
                          f' пользователю {message[1]} '
                          f'от {message[3]}\n{message[2]}')

    def edit_contacts(self) -> None:
        """ Метод добавления и удаления контактов. """

        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемого контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    CLIENT_LOGGER.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            # Проверка на возможность такого контакта
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        CLIENT_LOGGER.error('Не удалось отправить информацию на сервер.')


class ClientReader(threading.Thread, metaclass=ClientMaker):
    # """ Класс-приёмник сообщений с сервера.
    # Принимает сообщения, выводит в консоль."""
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self) -> None:
        """ Метод - обработчик сообщений других
        пользователей, поступающих с сервера.
        Принимает сообщения, выводит в консоль.
        Завершается при потере соединения.
        """
        while True:  # Основной цикл приёмника сообщений.
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # Если не сделать тут задержку,
            # то второй поток может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)
                # Принято некорректное сообщение
                except (IncorrectDataRecivedError, json.JSONDecodeError, NonDictInputError):
                    CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                        break
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionRefusedError, ConnectionResetError):
                    CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                    break
                # Если пакет корректно получен выводим в консоль и записываем в базу.
                else:
                    if ACTION in message \
                            and message[ACTION] == MESSAGE \
                            and SENDER in message \
                            and DESTINATION in message \
                            and MESSAGE_TEXT in message \
                            and message[DESTINATION] == self.account_name:
                        print(f'\nCообщение от {message[SENDER]}: "{message[MESSAGE_TEXT]}"')
                        # Захватываем работу с базой данных и сохраняем в неё сообщение
                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER],
                                                           self.account_name,
                                                           message[MESSAGE_TEXT])
                            except Exception as e:
                                print(e)
                                CLIENT_LOGGER.error('Ошибка взаимодействия с базой данных')

                        CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                           f'\n{message[MESSAGE_TEXT]}')
                    else:
                        CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')


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


@Log(CLIENT_LOGGER)
def contacts_list_request(sock: socket.socket, name: str) -> list[str]:
    """ Функция запроса контакт-листа.
    :param sock: Клиентский сокет.
    :param name: Имя пользователя.
    :return: Список с именами контактов из базы данных.
    """
    CLIENT_LOGGER.debug(f'Запрос контакт листа для пользователя {name}')
    request = {
        ACTION: GET_CONTACTS,
        TIME: datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A "),
        USER: name
    }
    CLIENT_LOGGER.debug(f'Сформирован запрос {request}')
    send_message(sock, request)
    answer = get_message(sock)
    CLIENT_LOGGER.debug(f'Получен ответ {answer}')
    if RESPONSE in answer and answer[RESPONSE] == 202:
        return answer[LIST_INFO]
    else:
        raise ServerError


@Log(CLIENT_LOGGER)
def add_contact(sock: socket.socket, username: str, contact: str) -> None:
    """ Функция добавления пользователя в контакт лист.
    :param sock: Клиентский сокет.
    :param username: Имя пользователя, к которому добавляется контакт.
    :param contact: Имя пользователя, который добавляется, как новый контакт.
    """

    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    request = {
        ACTION: ADD_CONTACT,
        TIME: datetime.now().strftime("%d %B %Yг | %H:%M:%S | %A "),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, request)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


@Log(CLIENT_LOGGER)
def remove_contact(sock: socket.socket, username: str, contact: str) -> None:
    """ Функция удаления пользователя из списка контактов.
    :param sock: Клиентский сокет.
    :param username: Имя пользователя, у кого нужно удалить контакт.
    :param contact: Контакт, который нужно удалить.
    """
    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


@Log(CLIENT_LOGGER)
def user_list_request(sock: socket.socket, username: str) -> list[str]:
    """ Функция запроса списка известных пользователей.
    :param sock: Клиентский сокет.
    :param username: Имя пользователя, который запросил всех известных.
    :return: Список имён всех известных пользователей.
    """
    CLIENT_LOGGER.debug(f'Запрос списка известных пользователей от {username}')
    request = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, request)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 202:
        return answer[LIST_INFO]
    else:
        raise ServerError


@Log(CLIENT_LOGGER)
def database_load(sock: socket.socket, database: ClientDatabase,
                  username: str) -> None:
    """ Функция инициализатор базы данных.
    Запускается при запуске, загружает данные в базу с сервера.
    :param sock: Клиентский сокет.
    :param database: Объект базы данных.
    :param username: Имя пользователя, который запросил всех известных.
    """
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        CLIENT_LOGGER.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        CLIENT_LOGGER.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    # Загружаем параметры командной строки и сообщаем о запуске в консоль.
    server_address, server_port, client_name = get_arg_commandline()
    print(f'Консольный месседжер. Клиентский модуль.')

    # На случай, если имя пользователя не было задано, изначально.
    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: '
                       f'адрес сервера: {server_address}, '
                       f'порт: {server_port}, '
                       f'имя пользователя: {client_name}')

    # Инициализация сокета и отправка сообщения серверу о нашем появлении.
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Таймаут 1 секунда, необходим для освобождения сокета.
        transport.settimeout(1)
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
    except (ConnectionError, ConnectionAbortedError,
            ConnectionRefusedError, ConnectionResetError):
        CLIENT_LOGGER.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    else:
        # Инициализация БД
        database = ClientDatabase(client_name)
        database_load(transport, database, client_name)

        # Запуск клиентского процесса приёма сообщений.
        module_reciver = ClientReader(client_name, transport, database)
        module_reciver.daemon = True
        module_reciver.start()
        CLIENT_LOGGER.debug('Запущены процессы чтения.')
        # Запуск отправки сообщений и взаимодействия с пользователем.
        module_sender = ClientSender(client_name, transport, database)
        module_sender.daemon = True
        module_sender.start()
        CLIENT_LOGGER.debug('Запущены процессы отправки.')

        # Watchdog основной цикл, если один из потоков завершён,
        # то значит или потеряно соединение, или пользователь ввёл exit.
        # Поскольку все события обработываются в потоках,
        # то достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if module_reciver.is_alive() and module_sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
