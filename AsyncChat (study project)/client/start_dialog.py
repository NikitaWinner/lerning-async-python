from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel , qApp, QMessageBox
from PyQt5.QtCore import QEvent


class UserNameDialog(QDialog):
    """ GUI - класс стартового окна с выбором имени пользователя """
    def __init__(self):
        super().__init__()
        self.ok_pressed = False
        self.messages = QMessageBox()
        self.setWindowTitle('Привет!')
        self.setFixedSize(260, 140)
        self.initUI()
        self.connects()
        self.show()

    def initUI(self):
        """ Инициализация и настройка виджетов окна """
        self.label = QLabel('Введите имя пользователя:', self)
        self.label.setFixedSize(200, 20)
        self.label.move(25, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(200, 30)
        self.client_name.move(25, 40)

        self.btn_ok = QPushButton('Начать', self)
        self.btn_ok.move(10, 85)

        self.btn_cancel = QPushButton('Выход', self)
        self.btn_cancel.move(130, 85)

    def connects(self):
        """ Метод подключает обработчики сигналов всех кнопок """
        self.btn_ok.clicked.connect(self.click)
        self.btn_cancel.clicked.connect(qApp.exit)

    def click(self):
        """ Обработчик кнопки ОК, если поле ввода
         не пустое, ставим флаг и завершаем приложение."""
        if self.client_name.text():
            self.ok_pressed = True
            qApp.exit()
        else:
            self.messages.information(self, 'Упс!', 'Введите свой логин, что бы продолжить.')



if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
