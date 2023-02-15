from show_result_module import show_type

WORD_BYTES_1 = b'class'
WORD_BYTES_2 = b'function'
WORD_BYTES_3 = b'method'

LIST_WORD_BYTES = [WORD_BYTES_1, WORD_BYTES_2, WORD_BYTES_3]
for word in LIST_WORD_BYTES:
    print(show_type(word))

