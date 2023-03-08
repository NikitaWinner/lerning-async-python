from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel , qApp, QMessageBox
from PyQt5.QtCore import QEvent


class UserNameDialog(QDialog):
    """ GUI - класс стартового окна с запросом логина и пароля
    пользователя."""
    def __init__(self):
        super().__init__()
        self.ok_pressed = False
        self.messages = QMessageBox()
        self.initUI()
        self.connects()
        self.show()

    def initUI(self):
        """ Инициализация и настройка виджетов окна """

        self.setWindowTitle('Вход')
        self.setFixedSize(260, 140)

        self.label = QLabel('Введите имя пользователя:', self)
        self.label.move(10, 10)
        self.label.setFixedSize(200, 20)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(154, 25)
        self.client_name.move(10, 30)

        self.btn_ok = QPushButton('Начать', self)
        self.btn_ok.move(10, 105)

        self.btn_cancel = QPushButton('Выход', self)
        self.btn_cancel.move(130, 105)

        self.label_passwd = QLabel('Введите пароль:', self)
        self.label_passwd.move(10, 55)
        self.label_passwd.setFixedSize(150, 20)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(154, 25)
        self.client_passwd.move(10, 75)
        self.client_passwd.setEchoMode(QLineEdit.Password)

    def connects(self):
        """ Метод подключает обработчики сигналов всех кнопок """
        self.btn_ok.clicked.connect(self.click)
        self.btn_cancel.clicked.connect(qApp.exit)

    def click(self):
        """ Обработчик кнопки ОК, если поле ввода имени и пароля
         не пустое, ставим флаг True и завершаем приложение."""
        if self.client_name.text() and self.client_passwd.text():
            self.ok_pressed = True
            qApp.exit()
        else:
            self.messages.information(self, 'Уведомление!', 'Введите свой логин и  пароль, что бы продолжить.')



if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
