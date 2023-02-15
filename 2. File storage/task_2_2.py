import json

def write_order_to_json(item, quantity, price, buyer, date):
    with open('data_file/orders.json', 'r', encoding='utf-8') as file_out:
        data_file = json.load(file_out)

    with open('data_file/orders.json', 'w', encoding='utf-8') as file_in:
        orders_list = data_file['orders']
        orders_info = dict(item=item, quantity=quantity, price=price, buyer=buyer, date=date)
        orders_list.append(orders_info)
        json.dump(data_file, file_in, indent=4, ensure_ascii=False)

# # initialisation (чтобы при отладке не удалять данные)
# with open('data_file/orders.json', 'w', encoding='utf-8') as f_in:
#     json.dump({'orders': []}, f_in, indent=4)


if __name__ == '__main__':
    write_order_to_json('printer', '10', '6700', 'Иванов I.I.', '24.09.2017')
    write_order_to_json('scaner', '20', '10000', 'Petrov P.P.', '11.01.2018')
