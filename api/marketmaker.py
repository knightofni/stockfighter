import json
import time
import threading

import arrow
import requests
import pandas as pd

from stockfighter import config
from .venue import StockFighterTrader
from .websockets import WebSocketListenerQuotes, WebSocketListenerFills

API_KEY = config.get('api', 'APIKEY')

class MarketBroker(object):
    """
        Main API.
            - Needs an instance of GameMaster to be instanciated
            - MarketMaker expects that the GameMaster instance has already started a level

        Capabilities :
            - send buy / sell orders            [buy, sell methods]
            - cancel orders                     [cancel methods]
            - show order book from API call     [order_book]
            - show own open orders              [show_pending_orders]
            - show past trades data             [get_histo]
            - show past bid / ask data          [get_spread]

    """
    _ORDER_TYPE = ('limit', 'market', 'fill-or-kill', 'immediate-or-cancel')

    def __init__(self, gm=None, update=3):
        # Extracts info from gamemaster
        if gm and gm.ready:
            self._gm = gm
            self._venue = gm.venues[0]
            self._stock = gm.tickers[0]
            self._account = gm.account
        elif gm and not gm.ready:
            raise Exception('GameMaster Not Ready')
        else:
            self._venue = 'TESTEX'
            self._stock = 'FOOBAR'
            self._account = 'EXB123456'
        # Instanciate a StockFighterTrade. Checks health of sf
        self._sft = StockFighterTrader(self._venue, self._stock)
        # Genetic API data
        self._headers = {
            'X-Starfighter-Authorization' : API_KEY
        }
        order_url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders"
        self._order_url = order_url.format(venue=self._venue, stock=self._stock)

        # Start a websocket listener for quotes
        self._wsq = WebSocketListenerQuotes(self)
        # # Creates a websocket connection for fills
        self._wsf = WebSocketListenerFills(self)

        # Starts polling loop
        self.all_orders_in_stock = dict()
        self._update = update
        thrd = threading.Thread(target=self._loop)
        thrd.start()

        print('Market Maker for stock {} initiated'.format(self._stock))


    """
        Standard API helpers
    """
    def _get_response(self, url):
        res = requests.get(url, headers=self._headers)
        return res.json()

    def _post_json(self, url, data):
        res = requests.post(url, data=json.dumps(data), headers=self._headers)
        return res.json()

    def _delete(self, url):
        res = requests.delete(url, headers=self._headers)
        return res.json()

    def _check_websocket_quotes_health(self):
        if not self._wsq.ws.live:
            data = self._wsq.ws.data.copy()
            self._wsq = WebSocketListenerQuotes(self, data)
            print('WebSocketListenerQuotes restarted')

    def _check_websocket_fills_health(self):
        if not self._wsf.ws.live:
            data = self._wsf.ws.data.copy()
            self._wsf = WebSocketListenerFills(self, data)
            print('WebSocketListenerFills restarted')

    """
        Market Data
    """
    def get_histo(self):
        self._check_websocket_quotes_health()
        return self._wsq.get_data()

    def get_spread(self):
        self._check_websocket_quotes_health()
        return self._wsq.get_spread()

    @property
    def order_book(self):
        return self._sft.order_book

    # def quote(self):  ## Still usefull ??
    #     return self._sft.get_quote(self._stock)

    def _get_fills_ws(self):
        # Data from the Fills websocket
        self._check_websocket_fills_health()
        return self._wsf.ws.data

    def get_latest_quote_time(self):
        # arrow time of the latest quote
        self._check_websocket_quotes_health()
        return self._wsq.get_latest_quote_time()

    def current_quote(self):
        # Get data on the latest quote
        df = self.get_spread()
        if not df.empty:
            return df.loc[df.index.max()]
        else:
            return pd.Series()
    """
        Past orders related. Updates list of open orders
    """

    # def show_pending_orders(self):
    #     """
    #         returns a sorted dataframe of pending orders
    #     """
    #     self._parse_live_orders()
    #     if len(self.openorders) > 0:
    #         raw = pd.DataFrame(self.openorders).sort_values(by='price', ascending=False)
    #         df = raw[['ts', 'id','direction', 'price', 'qty', 'totalFilled']]
    #         df['ts'] = pd.to_datetime(df['ts'])
    #         return df
    #     else:
    #         return pd.DataFrame()


    # def _parse_live_orders(self):
    #     """
    #         Checks all passed orders for stock.
    #         Splits the list between closed and pending orders
    #     """
    #     orders = self.get_all_orders_in_stock()
    #     self.openorders, self.closedorders = [], []
    #     for order in orders:
    #         if order.get('open'):
    #             self.openorders.append(order)
    #         else:
    #             self.closedorders.append(order)
    """
        Sends buy / sell orders
            - Will parse and store the execution result
            - can also cancel orders
    """

    def _post_send_order(self, qty, price, order_type, direction):
        if order_type not in self._ORDER_TYPE:
            raise Exception('order_type must be on of : [{}]'.format(', '.join(self._ORDER_TYPE)))

        if order_type != 'market' and not price:
            raise Exception('need a price for order_type {}'.format(order_type))


        order = {
            'account'  : self_account,
            'venue'    : self._venue,
            'stock'    : self._stock,
            'price'    : int(price),
            'qty'      : int(qty),
            'direction' : direction,
            'orderType' : order_type,
        }

        if qty > 0:
            res = self._post_json(self._order_url, order)
        else:
            print('Qty passed {} - not sending {} order'.format(qty, direction))
            res = dict()


        if res.get('ok'):
            return res
        elif res.get('error'):
            raise Exception('Order did not go through. API returned {}'.format(res.get('error')))
        else:
            return None


    def _buy(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        return self._post_send_order(qty, price, order_type, 'buy')

    def _sell(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        return self._post_send_order(qty, price, order_type, 'sell')


    def _cancel(self, oid):
        """
            Cancels order of id `oid`.
            Adds the execution result to self.closedorders
        """
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/{order}"
        url = url.format(venue=self._venue, stock=self._stock, order=oid)
        res = self._delete(url)
        self.closedorders.append(res)
        return res


    """
        API calls to get order status. Currently not used as the websocket seems to be providing
            similar results faster.
    """
    def _loop(self):
        while True:
            self.all_orders_in_stock = self._get_all_orders_in_stock()
            time.sleep(self._update)

    def get_order_status(self, oid):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/{oid}".format(venue=self._venue, stock=self._stock, oid=oid)
        res = self._get_response(url)
        if res.get('ok'):
            return res
        else:
            raise Exception('Didnt get proper data from get_order_status')

    def _get_all_orders_in_stock(self):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/accounts/{account}/stocks/{stock}/orders".format(venue=self._venue, stock=self._stock, account=self._account)
        res = self._get_response(url)
        if res.get('ok'):
            return res.get('orders')
        else:
            raise Exception('Didnt get proper data from get_all_orders_in_stock')

    def _get_all_orders(self):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/accounts/{account}/orders".format(venue=self._venue, account=self._account)
        res = self._get_response(url)
        if res.get('ok'):
            return res.get('orders')
        else:
            raise Exception('Didnt get proper data from get_all_orders')


