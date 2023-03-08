import sys
import socket
import inspect
import logging

from functools import wraps

sys.path.append('../../')
import logs.config_client_log
import logs.config_server_log


class Log:
    """ Декоратор, выполняющий логирование вызовов функций.
    Сохраняет события типа debug, содержащие
    информацию об имени вызываемой функции, параметры с которыми
    вызывается функция, и модуль, вызывающий функцию. """

    def __init__(self, logger=None):
        """ Декоратор с параметром - именем логгера. В client.py и server.py
        это будет:
        LOGGER = logging.getLogger('client')
        @Log(LOGGER)
        def function():
            pass
        Но в модуле utils.py параметр LOGGER мы указать не можем, поэтому
        по умолчанию, при вызове функции из utils.py, logger будет == None. """
        self.logger = logger

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            parent_func_name = inspect.currentframe().f_back.f_code.co_name
            module_name = inspect.currentframe().f_back.f_code.co_filename.split("/")[-1]
            if self.logger is None:
                """
                Если декоратор вызван из utils.py, то параметр logger не задан.
                Значит, определяем (и связываем) наш логер по имени модуля module_name
                """
                logger_name = module_name.replace('.py', '')
                self.logger = logging.getLogger(logger_name)
            self.logger.debug(f'Функция {func.__name__} вызвана из функции {parent_func_name} '
                              f'в модуле {module_name} с аргументами: {args}; {kwargs}')
            result = func(*args, **kwargs)
            return result

        return wrapper


class LoginRequired:
    """ Декоратор, проверяющий, что клиент авторизован на сервере.
    Проверяет, что передаваемый объект сокета находится в
    списке авторизованных клиентов.
    За исключением передачи словаря-запроса
    на авторизацию. Если клиент не авторизован,
    генерирует исключение TypeError. """
    def __call__(self, func):
        def checker(*args, **kwargs):
            # проверяем, что первый аргумент - экземпляр MessageProcessor
            # Импортить необходимо тут, иначе ошибка рекурсивного импорта.
            from server.core import MessageProcessor
            from common.settings import ACTION, PRESENCE
            if isinstance(args[0], MessageProcessor):
                found = False
                for arg in args:
                    if isinstance(arg, socket.socket):
                        # Проверяем, что данный сокет есть в словаре names класса
                        # MessageProcessor
                        for client in args[0].names:
                            if args[0].names[client] == arg:
                                found = True

                # Теперь надо проверить, что передаваемые аргументы не presence
                # сообщение. Если presence, то разрешаем
                for arg in args:
                    if isinstance(arg, dict):
                        if ACTION in arg and arg[ACTION] == PRESENCE:
                            found = True
                # Если не авторизован и не сообщение начала авторизации, то
                # вызываем исключение.
                if not found:
                    raise TypeError
            return func(*args, **kwargs)

        return checker
