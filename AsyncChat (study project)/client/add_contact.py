import sys
sys.path.append('../')
from client.transport import ClientTransport
from client.database import ClientDatabase
from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from logs.config_client_log import create_client_logger

logger = create_client_logger()


class AddContactDialog(QDialog):
    """ GUI - класс окна выбора контакта для добавления.
    Предлагает пользователю список возможных контактов и
    добавляет выбранный в контакты."""
    def __init__(self, transport: ClientTransport, database: ClientDatabase):
        """
        :param transport: Объект клиентской транспортной системы обмена сообщениями.
        :param database: Объект базы данных клиента.
        """
        super().__init__()
        self.transport = transport
        self.database = database

        self.initUI()
        self.connects()

        # Заполняем список возможных контактов
        self.possible_contacts_update()

    def initUI(self):
        """ Создание и настройка виджетов окна. """
        self.setFixedSize(350, 140)
        self.setWindowTitle('Выберите контакт для добавления:')
        # Удаляем диалог, если окно было закрыто преждевременно
        self.setAttribute(Qt.WA_DeleteOnClose)
        # Делаем это окно модальным (т.е. поверх других)
        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для добавления:', self)
        self.selector_label.setFixedSize(265, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 30)
        self.selector.move(10, 30)

        self.btn_refresh = QPushButton('Обновить список', self)
        self.btn_refresh.setFixedSize(150, 30)
        self.btn_refresh.move(30, 80)

        self.btn_ok = QPushButton('Добавить', self)
        self.btn_ok.setFixedSize(100, 30)
        self.btn_ok.move(230, 30)

        self.btn_cancel = QPushButton('Отмена', self)
        self.btn_cancel.setFixedSize(100, 30)
        self.btn_cancel.move(230, 70)

    def connects(self) -> None:
        """ Метод подключает слоты для обработки сигналов. """
        # Назначаем действие на кнопку обновить
        self.btn_refresh.clicked.connect(self.update_possible_contacts)
        # Действие выхода.
        self.btn_cancel.clicked.connect(self.close)

    def possible_contacts_update(self):
        """ Метод заполняет выпадающий список возможных контактов.
        Создаёт список всех зарегистрированных пользователей
        за исключением уже добавленных в контакты и самого себя. """
        self.selector.clear()
        # множества всех контактов и контактов клиента
        contacts_list = set(self.database.get_contacts())
        users_list = set(self.database.get_users())
        # Удалим сами себя из списка пользователей, чтобы нельзя было добавить самого себя
        users_list.remove(self.transport.username)
        # Добавляем список возможных контактов
        self.selector.addItems(users_list - contacts_list)

    def update_possible_contacts(self):
        """ Метод обновляет таблицу известных пользователей (забирает с сервера),
            затем обновляет содержимое окна предполагаемых контактов. """
        try:
            self.transport.user_list_update()
        except OSError:
            pass
        else:
            logger.debug('Обновление списка пользователей с сервера выполнено')
            self.possible_contacts_update()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from database import ClientDatabase
    database = ClientDatabase('test1')
    from transport import ClientTransport
    transport = ClientTransport('test1', '127.0.0.1', 7777, database)
    window = AddContactDialog(transport, database)
    window.show()
    app.exec_()
