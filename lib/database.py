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
        with self.db as tx:
            for order in list_orders.values():
                o = order.get('order')
                if 'fills' in o.keys():
                    o.pop('fills')
                tx['orders'].insert(o)

    def save_order(self, order):
        o = order.copy()
        o.pop('fills')
        self.db['orders'].insert(o)

    def iterate_table(self, table):
        for item in self.db[table]:
            yield item

