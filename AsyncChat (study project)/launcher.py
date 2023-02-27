"""Программа-лаунчер"""

import subprocess

process = []

while True:
    action = input(f'Выберите действие: '
                   f'q - выход , '
                   f's - запустить сервер, '
                   f'c - запустить клиенты '
                   f'x - закрыть все окна:')
    if action == 'q':
        break
    elif action == 's':
        # Запускаем сервер!
        process.append(subprocess.Popen('python server.py', shell=True))
    elif action == 'c':
        clients_count = int(input('Введите количество тестовых клиентов для запуска: '))
        # Запускаем клиентов:
        for i in range(clients_count):
            process.append(subprocess.Popen(f'python client.py -n test{i + 1}', shell=True))
    elif action == 'x':
        while process:
            process.pop().kill()
