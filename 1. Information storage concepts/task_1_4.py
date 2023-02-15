from show_result_module import str_bytes_conversion


WORD_1 = 'разработка'
WORD_2 = 'администрирование'
WORD_3 = 'protocol'
WORD_4 = 'standard'

LIST_WORD_STR = [WORD_1, WORD_2, WORD_3, WORD_4]

for word in LIST_WORD_STR:
    word_encode = str_bytes_conversion(word)
    word_decode = str_bytes_conversion(word_encode, decode=True)
    print(f'{word} -> {word_encode} -> {word_decode}')





