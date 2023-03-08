import sys
import hashlib
import binascii
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QPushButton, \
    QLineEdit, QApplication, QLabel, QMessageBox
sys.path.append('../')
from server.core import MessageProcessor
from server.database import ServerStorage


class RegisterUser(QDialog):
    """ GUI - класс диалог регистрации пользователя на сервере. """

    def __init__(self, database: ServerStorage, server: MessageProcessor):
        """
        :param database: Объект базы данных сервера.
        :param server: Объект обработчика сообщений сервера.
        """
        super().__init__()

        self.database = database
        self.server = server
        self.messages = QMessageBox()
        self.initUI()
        self.connects()

    def initUI(self) -> None:
        """ Создание и настройка виджетов окна. """
        # Настройки окна.
        self.setWindowTitle('Регистрация')
        self.setFixedSize(250, 183)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.label_username = QLabel('Введите имя пользователя:', self)
        self.label_username.move(10, 10)
        self.label_username.setFixedSize(220, 20)

        # Поле для ввода имени.
        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(154, 25)
        self.client_name.move(10, 30)

        self.label_passwd = QLabel('Введите пароль:', self)
        self.label_passwd.move(10, 55)
        self.label_passwd.setFixedSize(220, 20)

        # Поле для ввода пароля.
        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(154, 25)
        self.client_passwd.move(10, 75)
        self.client_passwd.setEchoMode(QLineEdit.Password)

        self.label_conf = QLabel('Подтвердите пароль:', self)
        self.label_conf.move(10, 100)
        self.label_conf.setFixedSize(220, 20)

        # Поле для ввода подтверждения пароля.
        self.client_conf = QLineEdit(self)
        self.client_conf.setFixedSize(154, 25)
        self.client_conf.move(10, 120)
        self.client_conf.setEchoMode(QLineEdit.Password)

        # Кнопка сохранения пароля.
        self.btn_ok = QPushButton('Сохранить', self)
        self.btn_ok.move(10, 150)

        # Кнопка закрытия окна.
        self.btn_cancel = QPushButton('Выход', self)
        self.btn_cancel.move(130, 150)

        self.show()

    def connects(self) -> None:
        """ Метод подключает слоты для обработки сигналов. """
        self.btn_ok.clicked.connect(self.save_data)
        self.btn_cancel.clicked.connect(self.close)

    def save_data(self) -> None:
        """ Метод проверки правильности ввода и сохранения в базу нового пользователя. """
        if not self.client_name.text():
            self.messages.critical(self, 'Ошибка', 'Не указано имя пользователя.')
            return
        elif self.client_passwd.text() != self.client_conf.text():
            self.messages.critical(self, 'Ошибка', 'Введённые пароли не совпадают.')
            return
        elif self.database.check_user(self.client_name.text()):
            self.messages.critical(self, 'Ошибка', 'Пользователь уже существует.')
            return
        else:
            # Генерируем хэш пароля, в качестве соли
            # будем использовать логин в нижнем регистре.
            password_bytes = self.client_passwd.text().encode('utf-8')
            salt = self.client_name.text().lower().encode('utf-8')
            password_hash = hashlib.pbkdf2_hmac('sha512', password_bytes,
                                                salt, 10000)
            username = self.client_name.text()
            password_hash_hex = binascii.hexlify(password_hash)
            self.database.add_user(username, password_hash_hex)
            self.messages.information(self, 'Уведомление!',
                                      'Пользователь успешно зарегистрирован.')
            # Рассылаем клиентам сообщение о необходимости обновить справочники.
            self.server.service_update_lists()
            self.close()


if __name__ == '__main__':
    app = QApplication([])
    from database import ServerStorage
    database = ServerStorage('../server_database.db3')
    import os
    import sys
    path1 = os.path.join(os.getcwd(), '..')
    sys.path.insert(0, path1)
    from core import MessageProcessor
    server = MessageProcessor('127.0.0.1', 7777, database)
    dial = RegisterUser(database, server)
    app.exec_()
