import sys
from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication, QListView, QLabel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor, QFont
from PyQt5.QtCore import pyqtSlot, QEvent, Qt
sys.path.append('../')
from client.main_window_conv import Ui_MainClientWindow
from client.add_contact import AddContactDialog
from client.del_contact import DelContactDialog
from client.database import ClientDatabase
from client.transport import ClientTransport
from client.start_dialog import UserNameDialog
from common.exceptions import ServerError
from logs.config_client_log import create_client_logger

logger = create_client_logger()

class ClientMainWindow(QMainWindow):
    """ GUI - класс основного окна. """
    def __init__(self, database: ClientDatabase, transport: ClientTransport):
        super().__init__()
        self.database = database
        self.transport = transport

        # Дополнительные требующиеся атрибуты.
        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None  # Текущий контакт с которым идёт обмен сообщениями.

        # Загружаем конфигурацию окна из Qt Designer.
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)
        self.ui.list_messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)

        # Подключение обработчиков сигналов.
        self.connects()

        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    def connects(self) -> None:
        """ Метод подключает все обработчики
        сигналов для кнопок на главном окне. """
        # Кнопка "Выход"
        self.ui.menu_exit.triggered.connect(qApp.exit)
        # Кнопка отправить сообщение
        self.ui.btn_send.clicked.connect(self.send_message)
        # "добавить контакт"
        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)
        # Удалить контакт
        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)
        # Double click по списку контактов отправляется в обработчик
        self.ui.list_contacts.clicked.connect(self.select_active_user)

    def set_disabled_input(self) -> None:
        """ Метод деактивирует поля ввода. """
        # Надпись  - получатель.
        self.ui.label_new_message.setText('Для выбора получателя '
                                          'дважды кликните на нем в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        # Поле ввода и кнопка отправки неактивны до выбора получателя.
        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

    def history_list_update(self) -> None:
        """ Метод заполняет историю сообщений. """
        # Получаем историю, отсортированную по дате.
        list_messages = sorted(self.database.get_history(self.current_chat),
                               key=lambda item: item[3])
        # Если модель не создана, создадим.
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)
        # Очистим от старых записей
        self.history_model.clear()
        # Берём не более 20 последних записей.
        length = len(list_messages)
        start_index = 0
        if length > 20:
            start_index = length - 20
        # Заполнение модели записями, так же стоит разделить входящие и исходящие
        # сообщения выравниванием и разным фоном.
        # Записи в обратном порядке, поэтому выбираем их с конца и не более 20
        for i in range(start_index, length):
            item = list_messages[i]
            if item[1] == 'in':
                mess = QStandardItem(f'{item[3].replace(microsecond=0).strftime("%H:%M | %B %d")}\n\n{item[2]}\n')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(39, 43, 58)))
                mess.setForeground(QBrush(QColor(255, 255, 255)))
                mess.setFont(QFont("Times", 8, QFont.Bold))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
            else:
                mess = QStandardItem(f'{item[3].replace(microsecond=0).strftime("%H:%M | %B %d")}\n\n{item[2]}\n')
                mess.setEditable(False)
                mess.setTextAlignment(Qt.AlignRight)
                mess.setBackground(QBrush(QColor(59, 133, 206)))
                mess.setForeground(QBrush(QColor(255, 255, 255)))
                mess.setFont(QFont("Times", 8, QFont.Bold))
                mess.setTextAlignment(Qt.AlignRight)
                self.history_model.appendRow(mess)
        self.ui.list_messages.scrollToBottom()

    def select_active_user(self) -> None:
        """ Метод-обработчик double click по контакту. """
        # Выбранный пользователем контакт находится в выделенном элементе в QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        # вызываем основную функцию
        self.set_active_user()

    def set_active_user(self) -> None:
        """ Метод, устанавливающий активного собеседника. """
        # Ставим надпись и активируем кнопки
        self.ui.label_new_message.setText('')
        self.ui.text_message.setPlaceholderText(f'Введите сообщение для {self.current_chat}...')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)

        # Заполняем окно историю сообщений по требуемому пользователю.
        self.history_list_update()

    def clients_list_update(self) -> None:
        """ Функция, обновляющая контакт-лист"""
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for username in sorted(contacts_list):
            item = QStandardItem(username)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def add_contact_window(self) -> None:
        """ Метод добавления контакта. """
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item: AddContactDialog) -> None:
        """ Метод - обработчик добавления, сообщает серверу,
        обновляет таблицу и список контактов. """
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact: str) -> None:
        """ Метод, добавляющий контакт в БД. """
        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Успешно добавлен контакт {new_contact}')
            self.messages.information(self, 'Успех', 'Контакт успешно добавлен.')

    def delete_contact_window(self) -> None:
        """Метод удаления контакта. """
        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item: DelContactDialog) -> None:
        """ Метод-обработчик удаления контакта: сообщает на сервер, обновляет таблицу контактов. """
        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            logger.info(f'Успешно удалён контакт {selected}')
            self.messages.information(self, 'Успех', 'Контакт успешно удалён.')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def send_message(self) -> None:
        """ Метод отправки сообщения пользователю. """
        # Текст в поле, проверяем что поле не пустое затем забирается сообщение и поле очищается
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        try:
            self.transport.send_message(self.current_chat, message_text)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
            self.close()
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            logger.debug(f'Отправлено сообщение для {self.current_chat}: {message_text}')
            self.history_list_update()

    # Слот приёма нового сообщений
    @pyqtSlot(str)
    def message(self, sender: str) -> None:
        """ Метод-слот приёма нового сообщений. """
        if sender == self.current_chat:
            self.history_list_update()
        else:
            # Проверим есть ли такой пользователь у нас в контактах:
            if self.database.check_contact(sender):
                # Если есть, спрашиваем о желании открыть с ним чат и открываем при желании
                if self.messages.question(self, 'Новое сообщение',
                                          f'Получено новое сообщение от {sender}, '
                                          f'открыть чат с ним?', QMessageBox.Yes,
                                          QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                print('NO')
                # Раз нет, спрашиваем хотим ли добавить юзера в контакты.
                if self.messages.question(self, 'Новое сообщение',
                              f'Получено новое сообщение от {sender}.\n '
                              f'Данного пользователя нет в вашем контакт-листе.\n'
                              f' Добавить в контакты и открыть чат с ним?',
                              QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.set_active_user()

    @pyqtSlot()
    def connection_lost(self) -> None:
        """ Метод-слот потери соединения. Выдаёт
        сообщение об ошибке и завершает работу приложения. """
        self.messages.warning(self, 'Сбой соединения', 'Потеряно соединение с сервером. ')
        self.close()

    def make_connection(self, trans_obj: ClientTransport):
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from database import ClientDatabase
    database = ClientDatabase('test1')
    from transport import ClientTransport
    transport = ClientTransport('test1', '127.0.0.1', 7777, database)
    window = ClientMainWindow(database, transport)
    sys.exit(app.exec_())
