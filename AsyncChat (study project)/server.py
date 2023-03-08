"""Программа-сервер"""

import os
import sys
import argparse
import configparser
from PyQt5.QtCore import Qt
from common.decorators import Log
from server.core import MessageProcessor
from PyQt5.QtWidgets import QApplication
from common.settings import DEFAULT_PORT
from server.database import ServerStorage
from server.main_window import MainWindow
from logs.config_server_log import create_server_logger


# Инициализация логгера для сервера.
SERVER_LOGGER = create_server_logger()


@Log(SERVER_LOGGER)
def get_arg_commandline(default_port: str, default_address: str) -> tuple:
    """ Создаём парсер аргументов командной строки
    и читаем параметры, возвращаем 3 параметра.
    :param default_port: Порты, с которых сервер принимает соединение.
    :param default_address: Ip-адрес сервера.
    :return: Возвращается кортеж из IP-адреса, порта, флага для графического интерфейса. """
    SERVER_LOGGER.debug(
        f'Инициализация парсера аргументов коммандной строки: {sys.argv}')
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    parser.add_argument('--no_gui', action='store_true')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    gui_flag = namespace.no_gui
    SERVER_LOGGER.debug('Аргументы успешно загружены.')
    return listen_address, listen_port, gui_flag

@Log(SERVER_LOGGER)
def config_load() -> configparser.ConfigParser:
    """ Парсер конфигурационного ini файла.
    :return: Настроенный экземпляр класса ConfigParser
             с данными конфигурации. """
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(os.path.join(dir_path, 'server_config.ini'))
    # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по умолчанию.
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config

@Log(SERVER_LOGGER)
def main() -> None:
    """ Основная функция. """
    # Загрузка файла конфигурации сервера.
    config = config_load()

    # Загрузка параметров командной строки, если нет параметров,
    # то задаются значения по умоланию из файла конфигурации.
    listen_address, listen_port, gui_flag = get_arg_commandline(config['SETTINGS']['Default_port'],
                                                                config['SETTINGS']['Listen_Address'])

    # Инициализация базы данных.
    path_to_database = os.path.join(config['SETTINGS']['Database_path'],
                                    config['SETTINGS']['Database_file'])
    database = ServerStorage(path_to_database)

    # Создание экземпляра класса - сервера и его запуск:
    server = MessageProcessor(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Если указан параметр без GUI, то запускаем простенький обработчик
    # консольного ввода
    if gui_flag:
        while True:
            command = input('Введите exit для завершения работы сервера.')
            if command == 'exit':
                # Если выход, то завершаем основной цикл сервера.
                server.running = False
                server.join()
                break

    # Если не указан запуск без GUI, то запускаем GUI:
    else:
        # Создаём графическое окружение для сервера:
        server_app = QApplication(sys.argv)
        server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        main_window = MainWindow(database, server, config)

        # Запускаем GUI
        server_app.exec_()

        # По закрытию окон останавливаем обработчик сообщений
        server.running = False


if __name__ == '__main__':
    main()
