import json
import socket
from common.settings import MAX_PACKAGE_LENGTH, ENCODING
from exceptions import NonDictInputError, IncorrectDataRecivedError
from decorators import Log


@Log()
def get_message(client: socket.socket) -> dict:
    """ Утилита приёма и декодирования сообщения. Принимает байты и
    выдаёт словарь, если принято что-то другое отдаёт ошибку значения """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        raise NonDictInputError
    raise IncorrectDataRecivedError


@Log()
def send_message(sock: socket.socket, message: dict) -> None:
    """ Утилита кодирования и отправки сообщения
    принимает словарь и отправляет его """

    if not isinstance(message, dict):
        raise NonDictInputError
    json_message = json.dumps(message)
    encoded_message = json_message.encode(ENCODING)
    sock.send(encoded_message)
