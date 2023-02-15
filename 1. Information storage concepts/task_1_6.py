from chardet import detect

FILENAME = 'test_file.txt'
WORD_1 = 'Сетевое программирование'
WORD_2 = 'Сокет'
WORD_3 = 'Декоратор'
LIST_WORD_STR = [WORD_1, WORD_2, WORD_3]


def write_word(filename: str, source_list: list[str]) -> None:
    """ Функци записывает строковые объекты из входящего списка в текстовый фаил
    :param source_list: список слов
    """
    with open(filename, 'w') as file:
        for word in source_list:
            file.write(f'{word}\n')


def encoding_convert(filename: str) -> None:
    """ Функция перезаписывает фаил в правильной кодировки
    :param filename:
    :return:
    """
    with open(filename, 'rb') as f:
        content_bytes = f.read()
    detected = detect(content_bytes)
    encoding = detected['encoding']
    content_text = content_bytes.decode(encoding)
    with open('test.txt', 'w', encoding='utf-8') as f:
        f.write(content_text)


write_word(FILENAME, LIST_WORD_STR)
encoding_convert(FILENAME)