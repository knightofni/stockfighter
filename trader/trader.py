import arrow
import numpy as np
import pandas as pd

class TraderBook(object):
    """
        Keeps Track of the book
            - closed orders
            - open orders
            - current position

    """

    def __init__(self, marketbroker):
        self.mb = marketbroker
        self._db = marketbroker._db
        self.book = {
            'position'   : {'qty' : 0, 'pps' : 0},
            'open_buy'   : {'qty' : 0, 'pps' : 0},
            'open_sell'   : {'qty' : 0, 'pps' : 0}
        }

        print('TraderBook Ready')


    def seconds_without_trading(self):
        # How many seconds since the last trade
        last_trade = arrow.get(self.mb.current_quote().name)
        last_quote = self.mb.get_latest_quote_time()
        return (last_quote - last_trade).total_seconds()


    """
        Orders related
    """
    def _store_order_result(self, res):
        """
            Stores the response from an order
        """
        res.pop('fills')
        self._db.save_order(res)

    def _update_orders(self):
        """
            Update status of orders - in database
                - get fills from websocket
                - find latest status for all the fills
                - for each record that exists in db, updates it.
        """
        orders = self.mb._get_fills_ws()
        latest_only = self._find_latest(orders)

        for oid, order in latest_only.items():
            oid_record = self._db.db['orders'].find_one(id=oid)
            if oid_record:
                update_data = order.get('order')
                if 'fills' in update_data:
                    update_data.pop('fills')
                self._db.db['orders'].update(update_data, keys=['id'])

    def flush_old_orders(self, seconds=120):
        # Cancel all open orders older than seconds
        all_orders = self.mb.all_orders_in_stock
        if all_orders:
            for order in all_orders:
                if order.get('open'):
                    if (arrow.get(order.get('ts')) < arrow.utcnow().replace(seconds= -seconds)):
                        self.cancel(order.get('id'))

    @staticmethod
    def _pos_and_price(data):
        """
            From a dataframe of qty & prices, returns the total qty, and the price per share
        """
        df = pd.DataFrame(data=data, columns=['qty', 'price'])

        if not df.empty:
            position = df.qty.sum()
            pps = np.average(df.price, weights=df.qty)
        else:
            position, pps = 0, 0

        return {'qty': position, 'pps': pps}

    def get_own_book(self):
        """
            Returns a tuple containing :
                - position : current number of owned / short shares
                - buy       : number of shares with open buy orders
                - sell      : number of shares with open sell orders
        """
        self._update_orders()

        filled_orders = []
        unfilled_orders = {
            'buy'    : [],
            'sell'   : [],

        }

        for o in self._db.iterate_table('orders'):
            # direction
            direction = 1 if o.get('direction') == 'buy' else -1
            # filled / unfilled
            filled = o.get('totalFilled')
            unfilled = o.get('originalQty') - filled
            price = o.get('price')
            ## Filled orders
            if filled > 0:
                filled_orders.append([filled * direction, price])

            if unfilled > 0 and o.get('open'):
                unfilled_orders[o.get('direction')].append([unfilled, price])

        self.book = {
            'position'  : self._pos_and_price(filled_orders),
            'open_buy'   : self._pos_and_price(unfilled_orders['buy']),
            'open_sell'   : self._pos_and_price(unfilled_orders['sell']),
        }

        return self.book

    def compute_pnl(self):
        qty = self.book.get('position').get('qty')
        pps = self.book.get('position').get('pps')
        if qty:
            self._market_value = (self.mb.get_histo().iloc[-1]['last'] / 100) * qty
            value = qty * pps / 100
            self.pnl = self._market_value - value
        else:
            self.pnl = None

        return self.pnl

    def buy(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        res = self.mb._buy(qty, price, order_type)
        if res:
            self._db.save_order(res)
        return res

    def sell(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        res = self.mb._sell(qty, price, order_type)
        if res:
            self._db.save_order(res)
        return res

    def cancel(self, oid):
        """
            cancel an order

                oid :
        """
        res = self.mb._cancel(oid)
        if res.get('ok') and not res.get('open'):
            print('Order {} cancelled successfully'.format(oid))
        else:
            raise Exception('Couldnt cancel order')


    """
        Fills related
    """
    def _find_latest(self, orders):
        """
            From a dictionnary of fills (returned by the fills websocket)
                filters, and return only the latest information
                (the fills dictionnary will contain one entry for each partial fill
                of an orderid )
        """
        latest_only = {}

        for order in orders:
            inid = order.get('incomingId')
            oid = order.get('order').get('id')

            if oid:
                soid = str(oid)
                if soid in latest_only.keys():
                    current_inid = latest_only.get(soid).get('incomingId')
                    if inid > current_inid:
                        latest_only[soid] = order
                else:
                    latest_only[soid] = order

        return latest_only
