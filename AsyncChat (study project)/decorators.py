import inspect
import logging
import sys

sys.path.append('../')
import logs.config_client_log
import logs.config_server_log
from functools import wraps


class Log:
    def __init__(self, logger=None):
        """
        Это декоратор с параметром - именем логера. В client.py и server.py
        это будет:

        LOGGER = logging.getLogger('client')

        @Log(LOGGER)
        def function():
            pass

        Но в модуле utils.py параметр LOGGER мы указать не можем, поэтому
        по умолчанию, при вызове функции из utils.py, logger будет == None.
        """
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
