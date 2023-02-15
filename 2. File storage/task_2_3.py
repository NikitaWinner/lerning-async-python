import yaml

DATA_IN = {'items': ['computer', 'printer', 'keyboard', 'mouse'],
           'items_quantity': 4,
           'items_price': {'computer': '200\u20ac-1000\u20ac',
                           'printer': '100\u20ac-300\u20ac',
                           'keyboard': '5\u20ac-50\u20ac',
                           'mouse': '4\u20ac-7\u20ac'}
           }

with open('data_file/data_result.yaml', 'w', encoding='utf-8') as f_in:
    yaml.dump(DATA_IN, f_in, default_flow_style=False, allow_unicode=True)

with open("data_file/data_result.yaml", 'r', encoding='utf-8') as f_out:
    DATA_OUT = yaml.load(f_out, Loader=yaml.SafeLoader)

print(DATA_IN == DATA_OUT)