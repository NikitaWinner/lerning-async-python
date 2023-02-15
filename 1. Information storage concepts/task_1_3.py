from show_result_module import is_str_to_bytes


WORD_1 = 'attribute'
WORD_2 = 'класс'
WORD_3 = 'функция'
WORD_4 = 'type'
LIST_WORD_STR = [WORD_1, WORD_2, WORD_3, WORD_4]

for word in LIST_WORD_STR:
    print(is_str_to_bytes(word))
