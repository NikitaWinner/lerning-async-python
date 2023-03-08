import os
import sys
from datetime import datetime
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine, Table, Column, \
    Integer, String, Text, DateTime
sys.path.append('..')


class ClientDatabase:
    """ Класс - оболочка для работы с базой данных клиента.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход. """

    class KnownUsers:
        """ Класс - отображение для таблицы всех пользователей. """

        def __init__(self, username: str):
            """ Конструктор класса KnownUsers.
            :param username: Уникальное имя пользователя
            """
            self.id = None  # primary_key
            self.username = username

    # class MessageStat:
    #     """ Класс - отображение для таблицы статистики переданных сообщений. """
    #
    #     def __init__(self, contact, direction, message):
    #         self.id = None
    #         self.contact = contact
    #         self.direction = direction
    #         self.message = message
    #         self.date = datetime.now()

    class MessageHistory:
        """ Класс - отображение для таблицы
        статистики переданных сообщений. """

        def __init__(self, contact: str, direction: str, message: str):
            """ Конструктор класса MessageHistory.
            :param contact: Имя пользователя - от кого сообщение.
            :param direction: Имя пользователя - кому сообщение.
            :param message: Текст сообщения. """
            self.id = None  # primary_key
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.now()

    class Contacts:
        """ Класс - отображение для таблицы списка контактов. """

        def __init__(self, contact: str):
            """ Конструкор класса Contacts.
            :param contact: Уникальное имя нового контакта.
            """
            self.id = None  # primary_key
            self.username = contact

    def __init__(self, client_name: str):
        """ Конструктор класса ClientDatabase.
        Создаёт движок базы данных, все таблицы,
        связывает их классы в ORM с таблицей sqlite
        и создаёт сессию для запросов. Поскольку разрешено
        несколько клиентов одновременно, каждый должен иметь свою БД.
        :param client_name: Имя клиента(пользователя)
        """

        # Создаём отображения для метаданных.
        self.mapper_registry = registry()

        # Создаём таблицу известных пользователей
        users_table = Table('Known_users', self.mapper_registry.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('username', String)
                      )

        # Создаём таблицу истории сообщений
        history_table = Table('Message_history', self.mapper_registry.metadata,
                        Column('id', Integer, primary_key=True),
                        Column('contact', String),
                        Column('direction', String),
                        Column('message', Text),
                        Column('date', DateTime)
                        )

        # Создаём таблицу контактов
        contacts_table = Table('Contacts', self.mapper_registry.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('username', String, unique=True)
                         )

        # Поскольку клиент мультипоточный, то необходимо отключить проверки
        # на подключения с разных потоков, иначе sqlite3.ProgrammingError
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{client_name}.db3'
        self.database_engine = create_engine(f'sqlite:///{os.path.join(path, filename)}',
                                             echo=False,
                                             pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        # Создаём таблицы
        self.mapper_registry.metadata.create_all(self.database_engine)

        # Создаём отображения
        self.mapper_registry.map_imperatively(self.KnownUsers, users_table)
        self.mapper_registry.map_imperatively(self.MessageHistory, history_table)
        self.mapper_registry.map_imperatively(self.Contacts, contacts_table)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Необходимо очистить таблицу контактов, т.к. при запуске они подгружаются с сервера.
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact: str) -> None:
        """ Метод добавления контактов в таблицу Contacts.
        :param contact: Имя контакта, которого нужно добавить. """
        # Проверяем, нет ли дубля.
        if not self.session.query(self.Contacts).filter_by(username=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact: str):
        """ Метод удаления контакта из таблицы Contacts.
        :param contact: Имя контакта, которого нужно удалить. """
        self.session.query(self.Contacts).filter_by(username=contact).delete()
        self.session.commit()

    def add_users(self, users_list: list[str]) -> None:
        """ Метод добавления известных пользователей в таблицу Known_users.
        Пользователи получаются только с сервера, поэтому таблица очищается.
        :param users_list: Список имён всех известных пользователей. """
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def contacts_clear(self):
        """ Метод очищает таблицу со списком контактов. """
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def save_message(self, contact: str, direction: str, message: str) -> None:
        """ Метод сохранения сообщений в таблицу Message_history.
        :param contact: Имя пользователя - от кого сообщение.
        :param direction: Отправленное или полученное.
        :param message: Текст сообщения. """
        message_row = self.MessageHistory(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self) -> list[str]:
        """ Метод возвращает все контакты.
        :return: Список имён контактов из таблицы Contacts. """
        all_contacts = [contact[0] for contact in self.session.query(self.Contacts.username).all()]
        return all_contacts

    def get_users(self) -> list[str]:
        """ Метод возвращает список известных пользователей.
        :return: Список имён известных пользователей из таблицы Known_users.
        """
        all_known_users = [user[0] for user in self.session.query(self.KnownUsers.username).all()]
        return all_known_users

    def check_user(self, user: str) -> bool:
        """ Метод проверяет наличие пользователя в таблице Known_users.
        :param user: Имя пользователя, которого нужно проверить.
        :return: True, если такой пользователь есть, иначе False. """
        if self.session.query(self.KnownUsers).filter_by(username=user).count():
            return True
        else:
            return False

    def check_contact(self, contact: str) -> bool:
        """ Метод проверяет наличие пользователя в таблице Contacts.
        :param contact: Имя контакта, которое нужно проверить.
        :return: True, если такой контакт есть, иначе False.
        """
        if self.session.query(self.Contacts).filter_by(username=contact).count():
            return True
        else:
            return False

    def get_history(self, contact: str) -> list[tuple]:
        """ Метод возвращает историю переписки.
        :param contact: Имя контакта с кем нужно получить историю переписки.
        :return: Список кортежей из имён отправителей, получателей,
                 текста сообщений и дат отправки.
        """
        query = self.session.query(self.MessageHistory).filter_by(contact=contact)
        history_message = [(history_row.contact, history_row.direction,
                            history_row.message, history_row.date)
                           for history_row in query.all()]
        return history_message


# отладка
if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    test_db.save_message('test1', 'test2',
                         f'Привет! я тестовое сообщение от {datetime.now().replace(microsecond=0)}!')
    test_db.save_message('test2', 'test1',
                         f'Привет! я другое тестовое сообщение от {datetime.now().replace(microsecond=0)}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_history('test2'))
    print(test_db.get_history(contact='test2'))
    print(sorted(test_db.get_history('test2'), key=lambda item: item[3]))
    test_db.del_contact('test4')
    print(test_db.get_contacts())
    print(test_db.get_history('test3'))
    test_db.del_contact('test4')
    print(test_db.get_contacts())
