"""Программа-клиент"""

import sys
import argparse
import threading
from common.decorators import Log
from PyQt5.QtWidgets import QApplication
from common.exceptions import ServerError
from client.database import ClientDatabase
from client.transport import ClientTransport
from client.start_dialog import UserNameDialog
from client.main_window import ClientMainWindow
from logs.config_client_log import create_client_logger
from common.settings import DEFAULT_PORT, DEFAULT_IP_ADDRESS


# Инициализация клиентского логгера.
CLIENT_LOGGER = create_client_logger()

# Объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


@Log(CLIENT_LOGGER)
def get_arg_commandline() -> tuple:
    """ Функция создаёт парсер аргументов коммандной строки
    и читает параметры при запуске модуля.
    :return: Возвращаем кортеж из IP-адреса, порта и логина клиента. """
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
    # Создаём клиенское приложение.
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке, то запросим его.
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект.
        # Иначе - выходим.
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    CLIENT_LOGGER.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , '
        f'порт: {server_port}, имя пользователя: {client_name}')

    # Создаём объект базы данных.
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток.
    try:
        transport = ClientTransport(client_name, server_address, server_port, database)
    except ServerError as error:
        print(error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()


if __name__ == '__main__':
    main()
