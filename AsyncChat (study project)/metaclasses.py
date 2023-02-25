import dis


class ServerMaker(type):
    """ Метакласс для проверки соответствия сервера:
    В основе метода библиотека dis - анализ кода с помощью его дизассемблирования
    (разбор кода на составляющие: в нашем случае - на атрибуты и методы класса) """

    def __init__(cls, clsname, bases, clsdict):
        methods = []  # Для методов, использующиеся в функциях класса.
        attrs = []  # Для атрибутов, использующиеся в функциях класса.
        for func in clsdict:
            try:
                instrs = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for instr in instrs:
                    if instr.opname == 'LOAD_GLOBAL':
                        if instr.argval not in methods:
                            methods.append(instr.argval)
                    elif instr.opname == 'LOAD_ATTR':
                        if instr.argval not in attrs:
                            attrs.append(instr.argval)
        # Если обнаружено использование недопустимого метода connect, вызываем исключение:
        if 'connect' in methods:
            raise TypeError('Использование метода connect недопустимо в серверном классе')
        # Если сокет не инициализировался константами SOCK_STREAM(TCP) AF_INET(IPv4), вызываем исключение.
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Некорректная инициализация сокета.')
        super().__init__(clsname, bases, clsdict)


class ClientMaker(type):
    """ Метакласс для проверки корректности клиентов
    В основе метода библиотека dis - анализ кода с помощью его дизассемблирования
    (разбор кода на составляющие: в нашем случае - на атрибуты и методы класса) """

    def __init__(cls, clsname, bases, clsdict):
        prohibited_methods = ('accept', 'listen')  # Запрещённые к использованию методы.
        methods = []
        for func in clsdict:
            try:
                instrs = dis.get_instructions(clsdict[func])
                # Если не метод, то ловим исключение
            except TypeError:
                pass
            else:
                for instr in instrs:
                    if instr.opname == 'LOAD_GLOBAL':
                        if instr.argval not in methods:
                            methods.append(instr.argval)
        # Если обнаружено использование недопустимого метода accept, listen, socket бросаем исключение:
        for command in prohibited_methods:
            if command in methods:
                raise TypeError('В классе обнаружено использование запрещённого метода.')
        # Вызов get_message или send_message из utils считаем корректным использованием сокетов
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError('Отсутствуют вызовы функций, работающих с сокетами.')
        super().__init__(clsname, bases, clsdict)
