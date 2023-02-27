from pprint import pprint
from datetime import datetime
from common.settings import SERVER_DATABASE
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine, Table, Column, \
    Integer, String, ForeignKey, DateTime


# print("Версия SQLAlchemy:", sqlalchemy.__version__)  # version: 2.0.4

class ServerStorage:
    """ Класс серверной базы данных. """

    class AllUsers:
        """ Класс для отображения таблицы всех пользователей
        Экземпляр этого класса - запись в таблице AllUsers. """

        def __init__(self, username: str):
            """
            :param username: Уникальный логин пользователя.
            """
            self.id = None  # primary_key
            self.name = username
            self.last_login = datetime.now()

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

    def __init__(self, path):
        """ Конструктор создаёт движок базы данных, все таблицы,
        связывает их классы в ORM с таблицей sqlite и создаёт сессию для запросов.
        :param path: Путь до файла базы данных.
        """

        # Создаём отображения для метаданных.
        self.mapper_registry = registry()
        # Создаём таблицу пользователей.
        all_users_table = Table('All_users', self.mapper_registry.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('name', String, unique=True),
                                Column('last_login', DateTime)
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

        # echo=False - отключает вывод на экран sql-запросов
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        # соединения через каждые 2 часа)
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

        # Создаём сессию.
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей.
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username: str, ip_address: str, port: int) -> None:
        """ Функция выполняющаяся при входе пользователя,
        записывает факт входа в таблицы ActiveUsers и LoginHistory.
        Если имя пользователя уже присутствует в таблице AllUsers,
        обновляет время последнего входа, если нет, то создаёт нового пользователя в AllUsers.
        :param username: Уникальный логин пользователя(клиента).
        :param ip_address: IP-адрес пользователя.
        :param port: Порт, с которого подключён пользователь.
        """
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем.
        all_users = self.session.query(self.AllUsers).filter_by(name=username)
        if all_users.count():
            user = all_users.first()
            user.last_login = datetime.now()
        else:
            # Создаём экземпляр класса self.AllUsers, через который передаём данные в таблицу.
            user = self.AllUsers(username)
            self.session.add(user)
            # Коммит здесь нужен для того, чтобы создать нового пользователя,
            # id которого будет использовано для добавления в таблицу активных пользователей.
            self.session.commit()
            user_in_history = self.UserHistory(user.id)
            self.session.add(user_in_history)

        # Создаём запись в таблицу активных пользователей о факте входа.
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.now())
        self.session.add(new_active_user)

        # Создаём экземпляр класса self.LoginHistory и сохранить в историю входов
        history = self.LoginHistory(user.id, ip_address, port, datetime.now())
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    def user_logout(self, username: str) -> None:
        """ Метод запрашивает пользователя, что покидает сервер
        и удаляет из таблицы Active_users этого пользователя.
        :param username: Уникальный логин пользователя, которого нужно удалить.
        """
        # Находим пользователя в представлении AllUsers
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        # Удаляем его из таблицы активных пользователей self.ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()
        self.session.commit()

    def process_message(self, sender: str, recipient: str) -> None:
        """ Метод фиксирует передачу и получение сообщения и увеличивает
        значения полей sent и accepted в таблице User_history """
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UserHistory).filter_by(user_id=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UserHistory).filter_by(user_id=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    def add_contact(self, username: str, contact: str) -> None:
        """ Метод добавляет контакт для пользователя.
        :param username: Имя пользователя, к которому добавляется контакт.
        :param contact: Имя пользователя, который добавляется, как новый контакт.
        """
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю пользователь(user) мы доверяем)
        if not contact or self.session.query(self.UserContacts).filter_by(user_id=user.id, contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UserContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user: str, contact: str) -> None:
        """ Функция удаляет контакт из таблицы User_contacts.
        :param user: Имя пользователя, у которого удаляется контакт.
        :param contact: Имя пользователя, который удаляется, как контакт.
        """
        # Получаем ID пользователей.
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь(user) мы доверяем)
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UserContacts).filter(
            self.UserContacts.user == user.id,
            self.UserContacts.contact == contact.id).delete())
        self.session.commit()

    def get_users_list(self) -> list[[tuple]]:
        """ Метод возвращает список известных пользователей
        со временем последнего входа.
        :return: Список кортежей из имён и времени последнего входа.
        """
        # Запрос пользователей из таблицы All_users.
        query = self.session.query(self.AllUsers.name,
                                   self.AllUsers.last_login)
        # Возвращаем список кортежей.
        return query.all()

    def get_active_users_list(self) -> list[[tuple]]:
        """ Функция возвращает список активных пользователей.
        :return: Список кортежей из имён, ip-адреса, порта и времени последнего входа.
        """
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(self.AllUsers.name,
                                   self.ActiveUsers.ip_address,
                                   self.ActiveUsers.port,
                                   self.ActiveUsers.login_time
                                   ).join(self.AllUsers)
        # Возвращаем список кортежей.
        return query.all()

    def get_login_history(self, username: str = None) -> list[[tuple]]:
        """ Метод запрашивает и возвращающает историю входов
        по конкретному пользователю или всем пользователям.
        :param username: Пользователь, по которому нужна история входов,
                         если None, то возвращается история входов по всем пользователям.
        :return: Список кортежей из имён, ip-адреса, порта и времени входа.
        """
        # Запрашиваем соединение таблиц для истории входа.
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.ip_address,
                                   self.LoginHistory.port,
                                   self.LoginHistory.date_time,
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по этому имени
        if username:
            query = query.filter(self.AllUsers.name == username)

        return query.all()

    def get_contacts(self, username: str) -> list[str]:
        """ Метод возвращает список контактов пользователя.
        :param username: Имя пользователя, чьи контакты хотим получить.
        :return: Список с именами контактов.
        """
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
                 кол-во отправленных и полученных сообщений.
        """
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
    # test_db = ServerStorage()
    # # Тестовые пользователи
    # test_db.user_login('client_1', '192.168.1.4', 8080)
    # test_db.user_login('client_2', '192.168.1.5', 7777)
    #
    # print('\nВыводим список кортежей - активных пользователей')
    # print(' ---- test_db.get_active_users_list() ----')
    # print(test_db.get_active_users_list(), '\n')
    #
    # print('Выполняем "отключение" пользователя client_1')
    # print('--- test_db.user_logout(client_1) ----\n')
    # test_db.user_logout('client_1')
    # print('Выводим список активных пользователей после отключения client_1')
    # print(' ---- test_db.get_active_users_list() ----')
    # print(test_db.get_active_users_list(), '\n')
    #
    # print('Запрашиваем историю входов по пользователю client_1')
    # print(' ---- test_db.get_login_history(client_1) ----')
    # print(test_db.get_login_history('client_1'), '\n')
    #
    # print('выводим список известных пользователей')
    # print(' ---- test_db.get_users_list() ----')
    # print(test_db.get_users_list(), '\n')
    test_db = ServerStorage('server_base.db3')
    test_db.user_login('1111', '192.168.1.113', 8080)
    test_db.user_login('McG2', '192.168.1.113', 8081)
    test_db.user_login('2222', '192.168.1.113', 8081)
    pprint(test_db.get_users_list())
    pprint(test_db.get_active_users_list())
    test_db.user_logout('McG2')
    pprint(test_db.get_login_history('re'))
    test_db.add_contact('McG2', '1111')
    test_db.add_contact('test1', 'test3')
    test_db.add_contact('1111', '2222')
    test_db.remove_contact('test1', 'test3')
    test_db.process_message('McG2', '1111')
    pprint(test_db.get_message_history())
