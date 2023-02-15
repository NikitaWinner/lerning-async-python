def show_type(word: str | bytes, show_len=False) -> str:
    """ Функция принимает строку
    и возвращает её содержимое, тип и длину.
    :param word: строка или байт
    :param show_len: Eсли True, то функция выводит длину, иначе ничего
    """
    item_len = f'len: {len(word)}' if show_len else ''
    return f'{word} | {type(word)} | {item_len}'


def is_str_to_bytes(word: str) -> str:
    """ Функция принимает строку и проверяет можно
    ли её преобразовать в байты
    :param word: строка
    :return: информационная строка-ответ
    """
    try:
        expr_obj = f"b'{word}'"
        return f"Строка {eval(expr_obj)} преобразована в байты!"
    except SyntaxError:
        return f'Строку "{word}" НЕЛЬЗЯ преобразовать в байты'


def str_bytes_conversion(word: str | bytes, decode: bool = False) -> str | bytes:
    """ Функция преобразовывает строки в байты и наоборот в зависимости от значения флагов
    :param word: принимает объект для преобразования
    :param decode: Если флаг True, то объект word декодируется из байтов,
                    если флаг False, то кодируется в байты
    :return преобразованый объект с типом bytes или str
    """
    if not decode:
        return word.encode('utf-8', 'ignore')
    return word.decode('utf-8', 'ignore')
