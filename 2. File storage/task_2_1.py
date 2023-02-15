import os
import re
import csv

import chardet


def get_data(dir: str):
    """ В функции осуществляется перебор файлов с данными, их открытие и считывание данных.
    :param dir:
    :return:
    """
    main_data = []
    os_prod_list = []
    os_name_list = []
    os_code_list = []
    os_type_list = []
    correct_filenames = []
    correct_extension = 'txt'
    for filename in os.listdir(dir):
        if filename.endswith(correct_extension):
            correct_filenames.append(filename)
    for correct_filename in correct_filenames:
        path_to_file = os.path.join(dir, correct_filename)
        with open(path_to_file, 'rb') as file_bytes:
            data_bytes = file_bytes.read()
            result = chardet.detect(data_bytes)
            data = data_bytes.decode(result['encoding'])
        # get a list of OS manufacturers
        os_prod_reg = re.compile(r'Изготовитель системы:\s*\S*')
        os_prod_list.append(os_prod_reg.findall(data)[0].split()[2])

        # get a list of OS names
        os_name_reg = re.compile(r'Windows\s\S*')
        os_name_list.append(os_name_reg.findall(data)[0])

        # get a list of products code
        os_code_reg = re.compile(r'Код продукта:\s*\S*')
        os_code_list.append(os_code_reg.findall(data)[0].split()[2])

        # get a list of systems type
        os_type_reg = re.compile(r'Тип системы:\s*\S*')
        os_type_list.append(os_type_reg.findall(data)[0].split()[2])

    headers = ['Изготовитель системы', 'Название ОС', 'Код продукта', 'Тип системы']
    main_data.append(headers)

    data_for_rows = [os_prod_list, os_name_list, os_code_list, os_type_list]  # matrix 4 x 3

    for idx in range(len(data_for_rows[0])):
        line = [row[idx] for row in data_for_rows]
        main_data.append(line)

    return main_data

def write_to_csv(out_file, input_dir):
    """Write the data to csv-file"""

    main_data = get_data(input_dir)

    with open(os.path.join(input_dir, out_file), 'w', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in main_data:
            writer.writerow(row)

if __name__ == '__main__':
    write_to_csv('data_result.csv', 'data_file')