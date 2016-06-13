import os

import dataset

class StockDataBase(object):
    _db_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    _name = 'stockfighter.db'

    def __init__(self, destroy=False):
        abs_path = os.path.join(self._db_path, self._name)
        if destroy:
            print('Removing Old StockDataBase.')
            if os.path.isfile(abs_path):
                os.remove(abs_path)

        print('Connecting to Database at : {}'.format(abs_path))
        self.db = dataset.connect('sqlite:///{}'.format(abs_path))

    def save_orders(self, list_orders):
        with self.db as tsx:
            for order in list_orders.values():
                order_copy = order.get('order')
                if 'fills' in order_copy.keys():
                    order_copy.pop('fills')
                tsx['orders'].insert(order_copy)

    def save_order(self, order):
        order_copy = order.copy()
        order_copy.pop('fills')
        self.db['orders'].insert(order_copy)

    def iterate_table(self, table):
        for item in self.db[table]:
            yield item

