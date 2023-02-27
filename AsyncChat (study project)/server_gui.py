import sys
from PyQt5.QtCore import Qt
from server_database import ServerStorage
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, \
    QLabel, QTableView, QDialog, QPushButton, QLineEdit, QFileDialog


def gui_create_model(database: ServerStorage) -> QStandardItemModel:
    """ Создание таблицы QModel, для отображения в окне программы.
    :param database: База данных сервера.
    :return: Список списков из данных всех активных пользователей. """
    active_users_list = database.get_active_users_list()
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
    return list_table


def create_stat_model(database: ServerStorage) -> QStandardItemModel:
    """GUI - Функция реализующая заполнение
    таблицы историей сообщений.
    :param database: База данных сервера.
    :return: Список списков полученных и переданных сообщений пользователей. """
    # Список записей из базы
    hist_list = database.get_message_history()

    # Объект модели данных:
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(
        ['Имя клиента', 'Последний раз входил', 'Отправлено', 'Получено'])
    for row in hist_list:
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

    return list_table


class MainWindow(QMainWindow):
    """ GUI - класс основного окна. """

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """ Созадние и настройка всех графических виджетов """

        # Настройки геометрии основного окна
        self.setWindowTitle('Управление сервером')
        self.setFixedSize(640, 600)

        # Кнопка выхода.
        self.exitAction = QAction(' Выход ', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        # Кнопка обновления списка клиентов.
        self.refresh_button = QAction('Обновить список ', self)

        # Кнопка вывода истории сообщений.
        self.show_history_button = QAction(' История клиентов ', self)

        # Кнопка настроек сервера.
        self.config_btn = QAction(' Настройки сервера ', self)

        # Статусбар
        self.statusBar()

        # Тулбар
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.exitAction)

        # Надпись о том, что ниже список подключённых клиентов
        self.label = QLabel('Список подключённых клиентов:', self)
        self.label.setFixedSize(400, 20)
        self.label.move(10, 30)

        # Окно со списком подключённых клиентов.
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 55)
        self.active_clients_table.setFixedSize(780, 400)

        # Последней командой отображаем окно.
        self.show()


class HistoryWindow(QDialog):
    """ GUI - класс окна с историей пользователей."""

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """ Созадние и настройка всех графических виджетов """

        # Настройки окна:
        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Кнопка закрытия окна
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        # Лист с собственно историей
        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(580, 620)

        # Последней командой отображаем окно.
        self.show()


class ConfigWindow(QDialog):
    """ GUI - класс окна настроек сервера. """

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """ Созадние и настройка всех графических виджетов """

        # Настройки окна
        self.setWindowTitle('Настройки сервера')
        self.setFixedSize(400, 300)

        # Надпись о файле базы данных:
        self.db_path_label = QLabel('Путь до файла базы данных: ', self)
        self.db_path_label.move(10, 8)
        self.db_path_label.setFixedSize(240, 20)

        # Строка с путём базы
        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 30)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        # Кнопка выбора пути.
        self.db_path_select = QPushButton('Обзор...', self)
        self.db_path_select.move(275, 28)

        def open_file_dialog() -> None:
            """ Метод-обработчик открытия окна выбора папки. """
            global dialog
            dialog = QFileDialog(self)
            path = dialog.getExistingDirectory()
            path = path.replace('/', '\\')
            self.db_path.insert(path)

        self.db_path_select.clicked.connect(open_file_dialog)

        # Метка с именем поля файла базы данных
        self.db_file_label = QLabel('Файл базы данных: ', self)
        self.db_file_label.move(10, 74)
        self.db_file_label.setFixedSize(200, 20)

        # Поле для ввода имени файла
        self.db_file = QLineEdit(self)
        self.db_file.move(240, 70)
        self.db_file.setFixedSize(150, 30)

        # Метка с номером порта
        self.port_label = QLabel('IP-адрес соединения:', self)
        self.port_label.move(10, 113)
        self.port_label.setFixedSize(250, 20)

        # Поле для ввода номера порта
        self.port = QLineEdit(self)
        self.port.move(240, 108)
        self.port.setFixedSize(150, 30)

        # Метка с адресом для соединений
        self.ip_label = QLabel('Номер порта для соединений:', self)
        self.ip_label.move(10, 150)
        self.ip_label.setFixedSize(250, 20)

        # Метка с напоминанием о пустом поле.
        self.ip_label_note = QLabel('(оставьте это поле пустым,\n чтобы принимать соединения с любых адресов)', self)
        self.ip_label_note.move(10, 170)
        self.ip_label_note.setFixedSize(500, 60)

        # Поле для ввода ip
        self.ip = QLineEdit(self)
        self.ip.move(240, 148)
        self.ip.setFixedSize(150, 30)

        # Кнопка сохранения настроек
        self.save_btn = QPushButton('Сохранить', self)
        self.save_btn.move(10, 255)

        # Кнопка закрытия окна
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(275, 255)
        self.close_button.clicked.connect(self.close)

        # Последней командой отображаем окно.
        self.show()


# Отладка
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.statusBar().showMessage('Test Statusbar Message')
    test_list = QStandardItemModel(main_window)
    test_list.setHorizontalHeaderLabels(
        ['Имя клиента        ', 'IP-адрес       ', 'Порт      ', 'Время подключения       '])
    test_list.appendRow(
        [QStandardItem('test1'), QStandardItem('192.198.0.5'), QStandardItem('23544'), QStandardItem('01:05:34')])
    test_list.appendRow(
        [QStandardItem('test2'), QStandardItem('192.198.0.8'), QStandardItem('33245'), QStandardItem('01:05:11')])
    main_window.active_clients_table.setModel(test_list)
    main_window.active_clients_table.resizeColumnsToContents()
    app.exec_()

    # ----------------------------------------------------------
    # app = QApplication(sys.argv)
    window = HistoryWindow()
    test_list = QStandardItemModel(window)
    test_list.setHorizontalHeaderLabels(
        ['Имя Клиента', 'Последний раз входил', 'Отправлено', 'Получено'])
    test_list.appendRow(
        [QStandardItem('test1'), QStandardItem('Fri Dec 12 16:20:34 2020'), QStandardItem('2'), QStandardItem('3')])
    test_list.appendRow(
        [QStandardItem('test2'), QStandardItem('Fri Dec 12 16:23:12 2020'), QStandardItem('8'), QStandardItem('5')])
    window.history_table.setModel(test_list)
    window.history_table.resizeColumnsToContents()

    # app.exec_()

    # ----------------------------------------------------------
    # app = QApplication(sys.argv)
    dial = ConfigWindow()

    app.exec_()
