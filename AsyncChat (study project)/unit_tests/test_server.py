"""Unit-тесты сервера"""

import sys
import os
import unittest
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
sys.path.append(os.path.join(os.getcwd(), '..'))
from common.settings import *
from server import process_client_message


class TestUtils(unittest.TestCase):
    '''
    Unit-тесты...В модуле сервере только 1 функция для тестирования.
    '''

    err_dict = RESPONSE_400
    err_dict[ERROR] = 'Запрос некорректен.'
    ok_dict = RESPONSE_200

    # инициализируем тестовые сокеты для клиента и для сервера
    server_socket = None
    client_socket = None

    def setUp(self) -> None:
        # Создаем тестовый сокет для сервера
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_socket.bind((DEFAULT_IP_ADDRESS, DEFAULT_PORT))
        self.server_socket.listen(MAX_CONNECTIONS)
        # Создаем тестовый сокет для клиента
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((DEFAULT_IP_ADDRESS, DEFAULT_PORT))
        self.client, self.client_address = self.server_socket.accept()

    def tearDown(self) -> None:
        # Закрываем созданные сокеты
        self.client.close()
        self.client_socket.close()
        self.server_socket.close()

    def test_ok_check(self):
        """Корректный запрос"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}, [], self.client, [], {}), self.ok_dict)

    def test_no_action(self):
        """Ошибка если нет действия"""
        self.assertEqual(process_client_message(
            {TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}, [], self.client, [], {}), self.err_dict)

    def test_wrong_action(self):
        """Ошибка если неизвестное действие"""
        self.assertEqual(process_client_message(
            {ACTION: 'Wrong', TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}, [], self.client, [], {}), self.err_dict)

    def test_no_time(self):
        """Ошибка, если  запрос не содержит штампа времени"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}, [], self.client, [], {}), self.err_dict)

    def test_no_user(self):
        """Ошибка - нет пользователя"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '1.1'}, [], self.client, [], {}), self.err_dict)

    def test_unknown_user(self):
        """Ошибка - не Guest"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest1'}}, [], self.client, [], {}), self.ok_dict)


if __name__ == '__main__':
    unittest.main()
