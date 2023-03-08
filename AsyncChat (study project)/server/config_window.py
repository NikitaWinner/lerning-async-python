import os
from configparser import ConfigParser
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt


class ConfigWindow(QDialog):
    """ GUI-класс окно настроек. """

    def __init__(self, config: ConfigParser):
        """
        :param config: Настройки конфигурации сервера.
        """
        super().__init__()
        self.config = config
        self.initUI()
        self.connects()

    def initUI(self) -> None:
        """ Создание и настройка виджетов окна. """
        # Настройки окна
        self.setWindowTitle('Настройки сервера')
        self.setFixedSize(400, 300)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

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
        self.db_path_select.clicked.connect(self.open_file_dialog)

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

        self.show()

        self.db_path.insert(self.config['SETTINGS']['Database_path'])
        self.db_file.insert(self.config['SETTINGS']['Database_file'])
        self.port.insert(self.config['SETTINGS']['Default_port'])
        self.ip.insert(self.config['SETTINGS']['Listen_Address'])


    def connects(self) -> None:
        """ Метод подключает слоты для обработки сигналов. """
        self.close_button.clicked.connect(self.close)
        self.save_btn.clicked.connect(self.save_server_config)

    def open_file_dialog(self) -> None:
        """ Метод-обработчик открытия окна выбора папки. """
        global dialog
        dialog = QFileDialog(self)
        path = dialog.getExistingDirectory()
        path = path.replace('/', '\\')
        self.db_path.clear()
        self.db_path.insert(path)

    def save_server_config(self) -> None:
        """ Метод сохранения настроек.
        Проверяет правильность введённых данных и
        если всё правильно сохраняет ini файл. """
        global config_window
        message = QMessageBox()
        self.config['SETTINGS']['Database_path'] = self.db_path.text()
        self.config['SETTINGS']['Database_file'] = self.db_file.text()
        try:
            port = int(self.port.text())
        except ValueError:
            message.warning(self, 'Ошибка', 'Порт должен быть числом')
        else:
            self.config['SETTINGS']['Listen_Address'] = self.ip.text()
            if 1023 < port < 65536:
                self.config['SETTINGS']['Default_port'] = str(port)
                dir_path = os.path.dirname(os.path.realpath(__file__))
                dir_path = os.path.join(dir_path, '..')
                with open(f"{dir_path}/{'server_dist+++.ini'}", 'w') as conf:
                    self.config.write(conf)
                    message.information(
                        self, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    self, 'Ошибка', 'Порт должен быть от 1024 до 65536')
