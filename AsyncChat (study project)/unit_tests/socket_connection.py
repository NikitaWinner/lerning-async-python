import sys

sys.path.append('../')
from common.settings import DEFAULT_IP_ADDRESS, DEFAULT_PORT, MAX_CONNECTIONS
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR

# Создаем тестовый сокет для сервера
server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server_socket.bind((DEFAULT_IP_ADDRESS, DEFAULT_PORT))
server_socket.listen(MAX_CONNECTIONS)

# Создаем тестовый сокет для клиента
client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect((DEFAULT_IP_ADDRESS, DEFAULT_PORT))

# Отправляем и получаем сообщение
client, address = server_socket.accept()
message = b'hi'
client_socket.send(message)
answer = client.recv(1024)
print(answer)
