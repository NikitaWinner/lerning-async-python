from show_result_module import show_type


WORD_1 = 'Декоратор'
WORD_2 = 'Разработка'
WORD_3 = 'Сокет'
LIST_WORD_STR = [WORD_1, WORD_2, WORD_3]
for word in LIST_WORD_STR:
    print(show_type(word))

WORD_UNICODE_1 = '\u0414\u0435\u043a\u043e\u0440\u0430\u0442\u043e\u0440'
WORD_UNICODE_2 = '\u0420\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0430'
WORD_UNICODE_3 = '\u0421\u043e\u043a\u0435\u0442'
LIST_WORD_UNICODE = [WORD_UNICODE_1, WORD_UNICODE_2, WORD_UNICODE_3]
for word in LIST_WORD_UNICODE:
    print(show_type(word))
