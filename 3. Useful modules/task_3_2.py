"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""

from task_3_1 import check_is_ipaddress, host_ping
from pprint import pprint


def host_range_ping(get_list: bool = False) -> host_ping:
    """
    Функция запрашивает первоначальный адрес и количество адресов,
    и далее, если в последнем октете есть возможность увеличивать адрес,
    функция возвращает список возможных адресов.
    Затем проверяет доступность этих адресов с пом ф-ции host_ping()
    :param get_list: Флаг, нужно ли отдать результат в виде словаря.
    :return: Словарь с результатами или вывод в консоль результатов
    в зависимости от значения флага get_list.
    """

    while True:
        start_ip = input("Введите первоначальный адрес: ")
        try:
            ipv4_start = check_is_ipaddress(start_ip)
            last_oct = int(start_ip.split('.')[3])  # Получаю последний октет ip-адреса.
            break
        except Exception as e:
            print(e)
    while True:
        end_ip = input("Сколько адресов проверить?: ")
        if not end_ip.isnumeric():
            print("Необходимо ввести число")
        else:
            if (last_oct + int(end_ip)) > 255+1:
                print(f"Можем менять только последний октет, "
                      f"т.е. максимальное число хостов {255+1 - last_oct}")
            else:
                break
    host_list = []
    [host_list.append(str(ipv4_start + x)) for x in range(int(end_ip))]  # Формируем список ip
    if not get_list:
        host_ping(host_list)
    else:
        return host_ping(host_list, True)


if __name__ == "__main__":
    pprint(host_range_ping(True))

