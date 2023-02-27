"""Unit-тесты клиента"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.settings import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE
from client import create_presence, process_ans
from common.exceptions import ReqFieldMissingError, ServerError


class TestClass(unittest.TestCase):
    '''
    Класс с unit-тестами
    '''

    def test_def_presense(self):
        """Тест коректного запроса"""
        test = create_presence()
        test[TIME] = 1.1  # время необходимо приравнять принудительно
        # иначе тест никогда не будет пройден
        self.assertEqual(test, {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}})

    def test_200_ans(self):
        """Тест корректного разбора ответа 200"""
        self.assertEqual(process_ans({RESPONSE: 200}), '200 : OK')

    def test_400_ans(self):
        """Тест корректного разбора 400"""
        self.assertRaises(ServerError, process_ans, {RESPONSE: 400, ERROR: 'Bad Request'})

    def test_no_response(self):
        """Тест исключения без поля RESPONSE"""
        self.assertRaises(ReqFieldMissingError, process_ans, {ERROR: 'Bad Request'})


if __name__ == '__main__':
    unittest.main()
