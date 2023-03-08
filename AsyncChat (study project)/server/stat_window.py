import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QDialog, QPushButton, QTableView
sys.path.append('../')
from server.database import ServerStorage

class StatWindow(QDialog):
    """ GUI-класс окна со статистикой пользователей. """

    def __init__(self, database: ServerStorage):
        """
        :param database: Объект базы данных сервера.
        """
        super().__init__()
        self.database = database
        self.initUI()
        self.connects()

    def initUI(self) -> None:
        """ Создание и настройка виджетов окна. """
        # Настройки окна:
        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Кнопка закрытия окна.
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)

        # Лист с собственно статистикой
        self.stat_table = QTableView(self)
        self.stat_table.move(10, 10)
        self.stat_table.setFixedSize(580, 620)

        self.create_stat_model()

    def connects(self) -> None:
        """ Метод подключает слоты для обработки сигналов. """
        self.close_button.clicked.connect(self.close)

    def create_stat_model(self) -> None:
        """ Метод реализующий заполнение таблицы статистикой сообщений. """
        # Список записей из базы
        stat_list = self.database.get_message_history()

        # Объект модели данных:
        list_table = QStandardItemModel()
        list_table.setHorizontalHeaderLabels(
            ['Имя клиента', 'Последний раз входил', 'Отправлено', 'Получено'])
        for row in stat_list:
            username, last_seen, sent, recvd = row
            username = QStandardItem(username)
            username.setEditable(False)
            last_seen = QStandardItem(str(last_seen.replace(microsecond=0).strftime("%H:%M %d %B %Yг")))
            last_seen.setEditable(False)
            sent = QStandardItem(str(sent))
            sent.setEditable(False)
            recvd = QStandardItem(str(recvd))
            recvd.setEditable(False)
            list_table.appendRow([username, last_seen, sent, recvd])
        self.stat_table.setModel(list_table)
        self.stat_table.resizeColumnsToContents()
        self.stat_table.resizeRowsToContents()
