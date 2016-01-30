import json
import random
import time

import arrow
import pandas as pd

from stockfighter import MarketBroker


class TraderBook(object):
    """
        Keeps Track of the book
            - closed orders
            - open orders
            - current position

    """

    def __init__(self, marketbroker):
        self.mb = marketbroker
        self.orders = dict()
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
        if res:
            oid = res.pop('id')
            self.orders[oid] = res

    def _update_orders(self):
        """
            Update status of orders
        """
        orders = self.mb._get_fills_ws()
        latest_only = self._find_latest(orders)

        for oid, order in latest_only.items():
            if oid in self.orders:
                self.orders[oid] = order

    def get_own_book(self):
        """
            Returns a tuple containing :
                - position : current number of owned / short shares
                - buy       : number of shares with open buy orders
                - sell      : number of shares with open sell orders
        """
        self._update_orders()
        sold = sum([order.get('totalFilled') for order in self.orders.values() if (not order.get('open') and order.get('direction') == 'sell')])
        bought = sum([order.get('totalFilled') for order in self.orders.values() if (not order.get('open') and order.get('direction') == 'buy')])
        position = bought - sold
        buy_open = sum([order.get('originalQty') - order.get('totalFilled') for order in self.orders.values() if (order.get('open') and order.get('direction') == 'buy')])
        sell_open = sum([order.get('originalQty') - order.get('totalFilled') for order in self.orders.values() if (order.get('open') and order.get('direction') == 'sell')])
        return (position, buy_open, sell_open)


    def buy(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        res = self.mb._buy(qty, price, order_type)
        self._store_order_result(res)
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
        self._store_order_result(res)
        return res

    def cancel(self, oid):
        """
            cancel an order

                oid :
        """
        res = self.mb._cancel(oid)
        return res

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

    def calculate_position(self):
        """
            Uses our stored orders to compute our position.
            Returns a tuple
                pps     - price paid per shares. Net cost of our purchases / sales, divided by
                        the total qty of shares we are long / short at the moment
                qty     - qty of shares we own (negative if we are short)
                nav     - our current PnL : cash + market_value
                            x cash          = aggregate cost of our purchases / sales
                            x market_value  = current market value of our position.
                                Using the price of the latet trade
        """
        orders = self.mb._get_fills_ws()
        latest_only = self._find_latest(orders)
        qty, value = 0, 0

        # Iterating the fills
        for oid, order in latest_only.items():
            direction = order.get('order').get('direction')
            dir_sign = 1 if direction == 'buy' else -1
            # aggregating all the partial fills of that order
            for fill in order.get('order').get('fills'):
                t_qty = fill.get('qty') * dir_sign
                t_price = fill.get('price')
                qty += t_qty
                value += t_qty * (t_price / 100)


        if qty != 0:
            pps = value / qty
            # market value of shares
            self._market_value = (self.mb.get_histo().iloc[-1]['last'] / 100) * qty
            self._cash = - value
            ret_val = (pps, qty, self._cash + self._market_value)
        else:
            ret_val = (None, 0, 0)

        return ret_val
