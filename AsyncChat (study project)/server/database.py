from datetime import datetime
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine, Table, Column, \
    Integer, String, ForeignKey, DateTime, Text


class ServerStorage:
    """ Класс - оболочка для работы с базой данных сервера.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход. """

    class AllUsers:
        """ Класс для отображения таблицы всех пользователей
        Экземпляр этого класса - запись в таблице AllUsers. """

        def __init__(self, username: str, password_hash: bytes):
            """
            :param username: Уникальный логин пользователя.
            :param password_hash: Хэш-пароль пользователя.
            """
            self.id = None  # primary_key
            self.name = username
            self.last_login = datetime.now()
            self.password_hash = password_hash
            self.pubkey = None

    class ActiveUsers:
        """ Класс для отображения таблицы активных пользователей:
        Экземпляр этого класса - запись в таблице ActiveUsers. """

        def __init__(self, user_id: int, ip_address: str, port: int, login_time: datetime):
            """
            :param user_id: Уникальный внешний ключ - 'All_users.id'.
            :param ip_address: IP-адрес пользователя.
            :param port: Порт, с которого подключился пользователь.
            :param login_time: Время последнего подключения.
            """
            self.id = None  # primary_key
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    class LoginHistory:
        """ Класс - отображение таблицы истории входов
        Экземпляр этого класса - запись в таблице LoginHistory """

        def __init__(self, user_id: int, ip_address: str, port: int, date: datetime):
            """
            :param user_id: Уникальный внешний ключ - 'All_users.id'.
            :param ip_address: IP-адрес пользователя.
            :param port: Порт, с которого подключился пользователь.
            :param date: Время входа(подключения).
            """
            self.id = None  # primary_key
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.date_time = date

    class UserContacts:
        """ Класс - отображение таблицы контактов пользователей. """

        def __init__(self, user_id: int, contact: int):
            """
            :param user_id: Уникальный внешний ключ - 'All_users.id'.
            :param contact: Уникальный внешний ключ - 'All_users.id'.
            """
            self.id = None  # primary_key
            self.user_id = user_id
            self.contact = contact

    class UserHistory:
        """ Класс - отображение таблицы истории действий. """

        def __init__(self, user_id: int):
            """
            :param user_id: Уникальный внешний ключ - 'All_users.id'.
            """
            self.id = None  # primary_key
            self.user_id = user_id
            self.sent = 0  # Кол-во отправленных сообщений.
            self.accepted = 0  # Кол-во полученных сообщений.

    def __init__(self, path: str):
        """ Конструктор создаёт движок базы данных, все таблицы,
        связывает их классы в ORM с таблицей sqlite и создаёт сессию для запросов.
        :param path: Путь до файла базы данных.
        """
        # Создаём отображения для метаданных.
        self.mapper_registry = registry()

        # Создаём таблицу пользователей
        all_users_table = Table('All_users', self.mapper_registry.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('name', String, unique=True),
                                Column('last_login', DateTime),
                                Column('password_hash', String),
                                Column('pubkey', Text)
                                )

        # Создаём таблицу активных пользователей.
        active_users_table = Table('Active_users', self.mapper_registry.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user_id', ForeignKey('All_users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Создаём таблицу истории входов.
        login_history_table = Table('Login_history', self.mapper_registry.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user_id', ForeignKey('All_users.id')),
                                    Column('ip_address', String),
                                    Column('port', Integer),  # String
                                    Column('date_time', DateTime)
                                    )

        # Создаём таблицу контактов пользователей
        user_contacts_table = Table('User_contacts', self.mapper_registry.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user_id', ForeignKey('All_users.id')),
                                    Column('contact', ForeignKey('All_users.id'))
                                    )

        # Создаём таблицу истории пользователей
        user_history_table = Table('User_history', self.mapper_registry.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user_id', ForeignKey('All_users.id')),
                                   Column('sent', Integer),
                                   Column('accepted', Integer)
                                   )

        self.database_engine = create_engine(f'sqlite:///{path}',
                                             echo=False,
                                             pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        # Создаём таблицы.
        self.mapper_registry.metadata.create_all(self.database_engine)

        # Связываем класс в ORM с таблицей.
        self.mapper_registry.map_imperatively(self.AllUsers, all_users_table)
        self.mapper_registry.map_imperatively(self.ActiveUsers, active_users_table)
        self.mapper_registry.map_imperatively(self.LoginHistory, login_history_table)
        self.mapper_registry.map_imperatively(self.UserContacts, user_contacts_table)
        self.mapper_registry.map_imperatively(self.UserHistory, user_history_table)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо
        # удалить
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username: str, ip_address: str, port: int, key: str) -> None:
        """ Функция выполняющаяся при входе пользователя,
        записывает факт входа в таблицы ActiveUsers и LoginHistory.
        Если имя пользователя уже присутствует в таблице AllUsers,
        обновляет время последнего входа, если нет, то создаёт нового пользователя в AllUsers.
        Обновляет открытый ключ пользователя при его изменении.
        :param username: Уникальный логин пользователя(клиента).
        :param ip_address: IP-адрес пользователя.
        :param port: Порт, с которого подключён пользователь.
        :param key: Ключ, для проверки пользователя.
        """
        # Запрос в таблицу пользователей на наличие там пользователя с таким
        # именем
        all_users = self.session.query(self.AllUsers).filter_by(name=username)

        # Если имя пользователя уже присутствует в таблице, обновляем время последнего входа
        # и проверяем корректность ключа. Если клиент прислал новый ключ,
        # сохраняем его.
        if all_users.count():
            user = all_users.first()
            user.last_login = datetime.now()
            if user.pubkey != key:
                user.pubkey = key
        # Если нет, то генерируем исключение
        else:
            raise ValueError('Пользователь не зарегистрирован.')

        # Теперь можно создать запись в таблицу активных пользователей о факте
        # входа.
        new_active_user = self.ActiveUsers(user.id, ip_address,
                                           port, datetime.now())
        self.session.add(new_active_user)

        # и сохранить в историю входов
        history = self.LoginHistory(user.id, ip_address,
                                    port, datetime.now())
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    def add_user(self, username: str, password_hash: bytes) -> None:
        """ Метод регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики.
        :param username: Уникальный логин пользователя.
        :param password_hash: Хэш-пароль. """
        new_user = self.AllUsers(username, password_hash)
        self.session.add(new_user)
        self.session.commit()
        history_row = self.UserHistory(new_user.id)
        self.session.add(history_row)
        self.session.commit()

    def remove_user(self, username: str) -> None:
        """ Метод удаляющий пользователя из базы.
        :param username: Уникальный логин пользователя."""
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()
        self.session.query(self.LoginHistory).filter_by(user_id=user.id).delete()
        self.session.query(self.UserContacts).filter_by(user_id=user.id).delete()
        self.session.query(self.UserContacts).filter_by(contact=user.id).delete()
        self.session.query(self.UserHistory).filter_by(user_id=user.id).delete()
        self.session.query(self.AllUsers).filter_by(name=username).delete()
        self.session.commit()

    def get_hash(self, username: str) -> bytes:
        """ Метод получения хэш-пароля пользователя.
        :param username: Уникальный логин пользователя.
        :return: Хэш-пароль пользователя из базы. """

        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        return user.password_hash

    def get_pubkey(self, username: str) -> str:
        """ Метод получения публичного ключа пользователя.
        :param username: Уникальный логин пользователя.
        :return: Публичный ключ пользователя из базы. """
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        return user.pubkey

    def check_user(self, username: str) -> bool:
        """ Метод проверяющий существование пользователя.
        :param username: Уникальный логин пользователя.
        :return: True, если пользователь есть в базе, иначе False """
        if self.session.query(self.AllUsers).filter_by(name=username).count():
            return True
        else:
            return False

    def user_logout(self, username: str) -> None:
        """ Метод фиксирующий отключения пользователя.
        :param username: Уникальный логин пользователя, которого нужно удалить. """
        # Находим пользователя в представлении AllUsers.
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        # Удаляем его из таблицы активных пользователей.
        self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()
        # Применяем изменения.
        self.session.commit()

    def process_message(self, sender: str, recipient: str) -> None:
        """ Метод фиксирует передачу и получение сообщения и увеличивает
        значения полей sent и accepted в таблице User_history
        :param sender: Уникальный логин отправителя.
        :param recipient: Уникальный логин отправителя. """
        # Получаем ID отправителя и получателя
        sender = self.session.query(
            self.AllUsers).filter_by(
            name=sender).first().id
        recipient = self.session.query(
            self.AllUsers).filter_by(
            name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(
            self.UserHistory).filter_by(
            user_id=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(
            self.UserHistory).filter_by(
            user_id=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    def add_contact(self, username: str, contact: str) -> None:
        """ Метод добавления контакта для пользователя.
        :param username: Имя пользователя, к которому добавляется контакт.
        :param contact: Имя пользователя, который добавляется, как новый контакт. """
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю
        # пользователь мы доверяем)
        if not contact or self.session.query(
                self.UserContacts).filter_by(user_id=user.id,
                                             contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        new_contact = self.UserContacts(user.id, contact.id)
        self.session.add(new_contact)
        self.session.commit()

    # Функция удаляет контакт из базы данных
    def remove_contact(self, username: str, contact: str) -> None:
        """ Функция удаляет контакт из таблицы User_contacts.
        :param username: Имя пользователя, у которого удаляется контакт.
        :param contact: Имя пользователя, который удаляется, как контакт. """
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы
        # доверяем)
        if not contact:
            return

        # Удаляем требуемое
        self.session.query(self.UserContacts).filter(self.UserContacts.user_id == user.id,
                                                     self.UserContacts.contact == contact.id).delete()
        self.session.commit()

    def get_users_list(self) -> list[[tuple]]:
        """ Метод возвращает список известных пользователей
        со временем последнего входа.
        :return: Список кортежей из имён и времени последнего входа. """
        # Запрос пользователей из таблицы All_users.
        query = self.session.query(self.AllUsers.name,
                                   self.AllUsers.last_login)
        # Возвращаем список кортежей.
        return query.all()

    def get_active_users_list(self) -> list[[tuple]]:
        """ Метод возвращает список активных пользователей.
        :return: Список кортежей из имён, ip-адреса, порта и времени последнего входа. """
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(self.AllUsers.name,
                                   self.ActiveUsers.ip_address,
                                   self.ActiveUsers.port,
                                   self.ActiveUsers.login_time
                                   ).join(self.AllUsers)
        # Возвращаем список кортежей.
        return query.all()

    def get_login_history(self, username: str = None) -> list[[tuple]]:
        """ Метод возвращает историю входов
        по конкретному пользователю или всем пользователям.
        :param username: Пользователь, по которому нужна история входов,
                         если None, то возвращается история входов по всем пользователям.
        :return: Список кортежей из имён, ip-адреса, порта и времени входа. """
        # Запрашиваем соединение таблиц для истории входа.
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.ip_address,
                                   self.LoginHistory.port,
                                   self.LoginHistory.date_time,
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по этому имени
        if username:
            query = query.filter(self.AllUsers.name == username)
        # Возвращаем список кортежей
        return query.all()

    def get_contacts(self, username: str) -> list[str]:
        """ Метод возвращает список контактов пользователя.
        :param username: Имя пользователя, чьи контакты хотим получить.
        :return: Список с именами контактов. """
        # Запрашиваем указанного пользователя.
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UserContacts, self.AllUsers.name). \
            filter_by(user_id=user.id). \
            join(self.AllUsers, self.UserContacts.contact == self.AllUsers.id)

        # Выбираем только имена пользователей и возвращаем их.
        contact_names = [contact[1] for contact in query.all()]
        return contact_names

    def get_message_history(self) -> list[[tuple]]:
        """ Метод возвращает количество переданных и полученных сообщений.
        :return: Список кортежей из имён пользователей, их времени входа,
                 кол-во отправленных и полученных сообщений. """
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UserHistory.sent,
            self.UserHistory.accepted
        ).join(self.AllUsers)

        # Возвращаем список кортежей
        return query.all()


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage('../server_database.db3')
    test_db.user_login('test1', '192.168.1.113', 8080, '123')
    test_db.user_login('test2', '192.168.1.113', 8081, '123')
    print(test_db.get_users_list())
    # print(test_db.active_users_list())
    # test_db.user_logout('McG')
    # print(test_db.login_history('re'))
    # test_db.add_contact('test2', 'test1')
    # test_db.add_contact('test1', 'test3')
    # test_db.add_contact('test1', 'test6')
    # test_db.remove_contact('test1', 'test3')
    test_db.process_message('test1', 'test2')
    print(test_db.get_message_history())
