from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, registry
from common.settings import *

print("Версия SQLAlchemy:", sqlalchemy.__version__)  # version: 2.0.4


class ServerStorage:
    """ Класс для серверной базы данных. """

    class AllUsers:
        """ Класс для отображения таблицы всех пользователей
        Экземпляр этого класса - запись в таблице AllUsers. """

        def __init__(self, username: str):
            """ Конструктор пользователя.
            :param username: Уникальный логин пользователя.
            """
            self.id = None  # primary_key
            self.name = username
            self.last_login = datetime.now()

    class ActiveUsers:
        """ Класс для отображения таблицы активных пользователей:
        Экземпляр этого класса - запись в таблице ActiveUsers. """

        def __init__(self, user_id: int, ip_address: str, port: int, login_time: datetime):
            """ Коструктор для данных активных пользователей(online)
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
            Коструктор для данных истории всех пользователей.
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

    def __init__(self):
        """ Конструктор создаёт движок базы данных, все таблицы,
        связываем их классы в ORM с таблицей sqlite и создаём сессию для запросов.
        """
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)
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
        user_login_history = Table('Login_history', self.mapper_registry.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user_id', ForeignKey('All_users.id')),
                                   Column('ip_address', String),
                                   Column('port', Integer),  # String
                                   Column('date_time', DateTime)
                                   )

        # echo=False - отключает вывод на экран sql-запросов
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        # соединения через каждые 2 часа)
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)

        # Создаём таблицы.
        self.mapper_registry.metadata.create_all(self.database_engine)

        # Связываем класс в ORM с таблицей.
        self.mapper_registry.map_imperatively(self.AllUsers, all_users_table)
        self.mapper_registry.map_imperatively(self.ActiveUsers, active_users_table)
        self.mapper_registry.map_imperatively(self.LoginHistory, user_login_history)

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

        # Создаём экземпляр класса self.ActiveUsers, через который передаём данные в таблицу.
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.now())
        self.session.add(new_active_user)

        # Создаём экземпляр класса self.LoginHistory, через который передаём данные в таблицу.
        history = self.LoginHistory(user.id, ip_address, port, datetime.now())
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    def user_logout(self, username: str) -> None:
        """ Метод запрашивает пользователя, что покидает нас
        и удаляет из таблицы Active_users этого пользователя.
        :param username: Уникальный логин пользователя, которого нужно удалить.
        """
        # Находим пользователя в представлении AllUsers
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        if user:
            # Удаляем его из таблицы активных пользователей.
            # Удаляем запись из таблицы self.ActiveUsers
            self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()
            self.session.commit()

    def get_users_list(self) -> list[[tuple]]:
        """ Метод возвращает список известных пользователей
        со временем последнего входа.
        :return: Список кортежей из имён и времени последнего входа.
        """
        # Запрос пользователей из таблицы All_users.
        query = self.session.query(self.AllUsers.name,
                                   self.AllUsers.last_login)
        return query.all()

    def get_active_users_list(self) -> list[tuple]:
        """ Функция возвращает список активных пользователей
        :return: Список кортежей из имён, ip-адреса, порта и времени последнего входа.
        """
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(self.AllUsers.name,
                                   self.ActiveUsers.ip_address,
                                   self.ActiveUsers.port,
                                   self.ActiveUsers.login_time
                                   ).join(self.AllUsers)

        return query.all()

    def get_login_history(self, username: str = None) -> list[[tuple]]:
        """ Метод запрашивает и возвращающает историю входов
        по конкретному пользователю или всем пользователям
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


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage()
    # Тестовые пользователи
    test_db.user_login('client_1', '192.168.1.4', 8080)
    test_db.user_login('client_2', '192.168.1.5', 7777)

    print('\nВыводим список кортежей - активных пользователей')
    print(' ---- test_db.get_active_users_list() ----')
    print(test_db.get_active_users_list(), '\n')

    print('Выполняем "отключение" пользователя client_1')
    print('--- test_db.user_logout(client_1) ----\n')
    test_db.user_logout('client_1')
    print('Выводим список активных пользователей после отключения client_1')
    print(' ---- test_db.get_active_users_list() ----')
    print(test_db.get_active_users_list(), '\n')

    print('Запрашиваем историю входов по пользователю client_1')
    print(' ---- test_db.get_login_history(client_1) ----')
    print(test_db.get_login_history('client_1'), '\n')

    print('выводим список известных пользователей')
    print(' ---- test_db.get_users_list() ----')
    print(test_db.get_users_list(), '\n')
