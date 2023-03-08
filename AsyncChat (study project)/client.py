"""Программа-клиент"""
import os
import sys
import argparse
import threading
from Crypto.PublicKey import RSA
from common.decorators import Log
from common.exceptions import ServerError
from client.database import ClientDatabase
from client.transport import ClientTransport
from client.start_dialog import UserNameDialog
from client.main_window import ClientMainWindow
from PyQt5.QtWidgets import QApplication, QMessageBox
from logs.config_client_log import create_client_logger
from common.settings import DEFAULT_PORT, DEFAULT_IP_ADDRESS


# Инициализация клиентского логгера.
CLIENT_LOGGER = create_client_logger()

# Объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


@Log(CLIENT_LOGGER)
def get_arg_commandline() -> tuple:
    """ Функция создаёт парсер аргументов командной строки
    и читает параметры при запуске модуля.
    Выполняет проверку на корректность номера порта.
    :return: Возвращаем кортеж из IP-адреса, порта, логина и пароля клиента. """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    # проверка подходящего номера порта.
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        sys.exit(1)

    return server_address, server_port, client_name, client_passwd


def main():
    # Загружаем параметры командной строки и сообщаем о запуске в консоль.
    server_address, server_port, client_name, client_password = get_arg_commandline()
    CLIENT_LOGGER.debug('Args loaded')
    # Создаём клиентское приложение.
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке, то запросим его
    start_dialog = UserNameDialog()
    if not client_name or not client_password:
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и
        # удаляем объект, иначе выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_password = start_dialog.client_passwd.text()
            CLIENT_LOGGER.debug(f'Using USERNAME = {client_name}, PASSWORD = {client_password}.')
        else:
            exit(0)

    # Записываем логи
    CLIENT_LOGGER.info(
        f'Запущен клиент с параметрами: адрес сервера: {server_address} , порт: {server_port},'
        f' имя пользователя: {client_name}')

    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    # !!!keys.publickey().export_key()
    CLIENT_LOGGER.debug("Keys successfully loaded.")
    # Создаём объект базы данных
    database = ClientDatabase(client_name)
    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(client_name, server_address, server_port,
                                    database, client_password, keys)
        CLIENT_LOGGER.debug("Transport ready.")
    except ServerError as error:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', error.text)
        exit(1)
    transport.daemon = True
    transport.start()

    # Удалим объект диалога за ненадобностью
    del start_dialog

    # Создаём GUI
    main_window = ClientMainWindow(database, transport, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()


if __name__ == '__main__':
    main()
