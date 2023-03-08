import sys
from configparser import ConfigParser
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QTimer
from server.stat_window import StatWindow
from server.config_window import ConfigWindow
from server.add_user import RegisterUser
from server.remove_user import DelUserDialog
sys.path.append('../')
from server.core import MessageProcessor
from server.database import ServerStorage


class MainWindow(QMainWindow):
    """ GUI-класс основного окна сервера. """

    def __init__(self, database: ServerStorage, server: MessageProcessor, config: ConfigParser):
        """
        :param database: Объект базы данных сервера.
        :param server: Объект обработчика сообщений сервера.
        :param config: Объект с данными конфигурации сервера.
        """
        super().__init__()

        self.database = database
        self.server_thread = server
        self.config = config

        self.initUI()
        self.connects()

    def initUI(self) -> None:
        """ Создание и настройка виджетов окна. """
        # Ярлык выхода
        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        # Кнопка обновить список клиентов
        self.refresh_button = QAction('Обновить список', self)

        # Кнопка настроек сервера
        self.config_btn = QAction('Настройки сервера', self)

        # Кнопка регистрации пользователя
        self.register_btn = QAction('Регистрация пользователя', self)

        # Кнопка удаления пользователя
        self.remove_btn = QAction('Удаление пользователя', self)

        # Кнопка вывести историю сообщений
        self.show_history_button = QAction('История клиентов', self)

        # Статусбар
        self.statusBar()
        self.statusBar().showMessage('Server Working')

        # Горизонтальное меню инструментов.
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.register_btn)
        self.toolbar.addAction(self.remove_btn)

        # Настройки геометрии основного окна
        # Поскольку работать с динамическими размерами мы не умеем, и мало
        # времени на изучение, размер окна фиксирован.
        self.setWindowTitle('Управление сервером')
        self.setFixedSize(640, 600)

        # Надпись о том, что ниже список подключённых клиентов
        self.label = QLabel('Список подключённых клиентов:', self)
        self.label.setFixedSize(400, 20)
        self.label.move(10, 30)

        # Окно со списком подключённых клиентов.
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 55)
        self.active_clients_table.setFixedSize(780, 400)

        # Таймер, обновляющий список клиентов 1 раз в секунду
        self.timer = QTimer()
        self.timer.timeout.connect(self.create_users_model)
        self.timer.start(1000)


        # Последней командой отображаем окно.
        self.show()

    def connects(self) -> None:
        """ Метод подключает слоты для обработки сигналов. """
        # Связываем кнопки с процедурами
        self.refresh_button.triggered.connect(self.create_users_model)
        self.show_history_button.triggered.connect(self.show_statistics)
        self.config_btn.triggered.connect(self.server_config)
        self.register_btn.triggered.connect(self.register_user)
        self.remove_btn.triggered.connect(self.remove_user)

    def create_users_model(self) -> None:
        """ Метод заполняющий таблицу активных пользователей. """
        active_users_list = self.database.get_active_users_list()
        # Создаём объект модели данных.
        list_table = QStandardItemModel()
        list_table.setHorizontalHeaderLabels(
            ['Имя клиента         ', 'IP-адрес         ', 'Порт       ', 'Время подключения       '])
        for row in active_users_list:
            user, ip, port, time = row
            user = QStandardItem(user)
            user.setEditable(False)
            ip = QStandardItem(ip)
            ip.setEditable(False)
            port = QStandardItem(str(port))
            port.setEditable(False)
            time = QStandardItem(str(time.replace(microsecond=0).strftime("%H:%M | %d %B %Yг")))
            time.setEditable(False)
            list_table.appendRow([user, ip, port, time])
        self.active_clients_table.setModel(list_table)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def show_statistics(self) -> None:
        """ Метод создающий окно со статистикой клиентов. """
        global stat_window
        stat_window = StatWindow(self.database)
        stat_window.show()

    def server_config(self) -> None:
        """ Метод создающий окно с настройками сервера. """
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow(self.config)

    def register_user(self) -> None:
        """ Метод создающий окно регистрации пользователя. """
        global reg_window
        reg_window = RegisterUser(self.database, self.server_thread)
        reg_window.show()

    def remove_user(self) -> None:
        """ Метод создающий окно удаления пользователя. """
        global rem_window
        rem_window = DelUserDialog(self.database, self.server_thread)
        rem_window.show()
if __name__ == '__main__':
    test = MainWindow(None, None, None)