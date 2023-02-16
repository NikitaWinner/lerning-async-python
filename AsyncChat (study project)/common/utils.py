"""Утилиты"""

import json
from common.settings import MAX_PACKAGE_LENGTH, ENCODING


def get_message(client):
    """
    Утилита приёма и декодирования сообщения.
    Принимает байты, выдаёт словарь, если принято что-то
    другое возвращает ValueError (ошибку значения)
    """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    message_error = 'Ответ должен быть закодирован в байты'
    if isinstance(encoded_response, bytes):
        message_error = 'Невозможно декодировать ответ в JSON-формат'
        json_response = encoded_response.decode(ENCODING)
        if isinstance(json_response, str):
            message_error = 'Не удалось десериализовать JSON-формат'
            response = json.loads(json_response)
            if isinstance(response, dict):
                return response
            raise ValueError(message_error)
        raise ValueError(message_error)
    raise ValueError(message_error)


def send_message(sock, message):
    """
    Утилита кодирования и отправки сообщения:
    принимает для отправки словарь, получает из него строку,
    далее превращает строку в байты и отправляет.
    """
    if not isinstance(message, dict):
        message_error = 'Некорректный тип сообщения перед отправкой'
        raise TypeError(message_error)
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)