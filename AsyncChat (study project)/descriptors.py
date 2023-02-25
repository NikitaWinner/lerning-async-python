from logs.config_server_log import create_server_logger

SERVER_LOGGER = create_server_logger()


class Port:
    """ Дескриптор для описания порта """

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            SERVER_LOGGER.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
