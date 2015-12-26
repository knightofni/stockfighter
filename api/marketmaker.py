import json
import random
import time

import requests
import websocket
import pandas as pd

from stockfighter import config
from .websockets import WebSocketListenerQuotes, WebSocketListenerFills

API_KEY = config.get('api', 'APIKEY')

class StockFighterTrader(object):
    """
        - Checks health of API on construction
        - Used for API calls that do not need authentication
    """
    def __init__(self, venue):
        self.venue = venue
        if not self._isonline():
            raise Exception('Stockfighter not online')
        if not self._venue_online(venue):
            raise Exception('Venue {} not online'.format(venue))

        print('StockFighterTrader initiated')

    def _get_response(self, url):
        r = requests.get(url)
        return r.json()

    def _isonline(self):
        url = 'https://api.stockfighter.io/ob/api/heartbeat'
        res = self._get_response(url)
        return res['ok']

    def _venue_online(self, venue):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/heartbeat".format(**{'venue' : venue})
        res = self._get_response(url)
        return res['ok']

    def get_quote(self, ticker):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/quote".format(venue=self.venue, stock=ticker)
        res = self._get_response(url)
        return res

    def order_book(self, ticker):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}".format(venue=self.venue, stock=ticker)
        res = self._get_response(url)
        return res



class MarketMaker(object):
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

    def __init__(self, gm=None):
        # Extracts info from gamemaster
        if gm:
            self.gm = gm
            self.venue = gm.venues[0]
            self.stock = gm.tickers[0]
            self.account = gm.account
        else:
            self.venue = 'TESTEX'
            self.stock = 'FOOBAR'
            self.account = 'EXB123456'
        # list for orders
        self.openorders        =    []
        self.closedorders      =    []

        # Instanciate a StockFighterTrade. Checks health of sf
        self._sft = StockFighterTrader(self.venue)
        # Genetic API data
        self._headers = {
            'X-Starfighter-Authorization' : API_KEY
        }
        order_url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders"
        self._order_url = order_url.format(venue=self.venue, stock=self.stock)

        # Start a websocket listener for quotes
        self._wsq = WebSocketListenerQuotes(self)
        # # Creates a websocket connection for fills
        self._wsf = WebSocketListenerFills(self)
        print('Market Maker for stock {} initiated'.format(self.stock))


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

    """
        Market Data
    """
    def get_histo(self):
        return self._wsq.get_data()

    def get_spread(self):
        return self._wsq.get_spread()

    def order_book(self):
        return self._sft.order_book(self.stock)

    def quote(self):  ## Still usefull ??
        return self._sft.get_quote(self.stock)

    """
        Fills related
    """
    def _get_fills_ws(self):
        # Data from the Fills websocket
        return self._wsf.ws.data

    def _parse_fills(self):
        """
            Checks own fills from websocket data. Not sure how to use this yet
        """
        fills= self._get_fills_ws()

        return  fills

    """
        Past orders related. Updates list of open orders
    """

    def show_pending_orders(self):
        """
            returns a sorted dataframe of pending orders
        """
        self._parse_live_orders()
        if len(self.openorders) > 0:
            return pd.DataFrame(self.openorders).sort_values(by='price', ascending=False)[['direction', 'price', 'qty', 'totalFilled']]
        else:
            return pd.DataFrame()


    def _parse_live_orders(self):
        """
            Checks all passed orders for stock.
            Splits the list between closed and pending orders
        """
        orders = self.get_all_orders_in_stock()
        self.openorders, self.closedorders = [], []
        for order in orders:
            if order.get('open'):
                self.openorders.append(order)
            else:
                self.closedorders.append(order)
    """
        Sends buy / sell orders
            - Will parse and store the execution result
            - can also cancel orders
    """

    def _post_send_order(self, price, qty, order_type, direction):
        if order_type not in self._ORDER_TYPE:
            raise Exception('order_type must be on of : [{}]'.format(', '.join(self._ORDER_TYPE)))

        if order_type != 'market' and not price:
            raise Exception('need a price for order_type {}'.format(order_type))

        order = {
            'account'  : self.account,
            'venue'    : self.venue,
            'stock'    : self.stock,
            'price'    : price,
            'qty'      : qty,
            'direction' : direction,
            'orderType' : order_type,
        }

        res = self._post_json(self._order_url, order)
        self._store_order_result(res)
        return res

    def _store_order_result(self, res):
        """
            Stores the response from an order
                If live, goes to self.openorders
                If Closed, goes to self.closedorders
        """
        live = res.get('open')
        if live:
            self.openorders.append(res)
        else:
            self.closedorders.append(res)

    def buy(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        return self._post_send_order(price, qty, order_type, 'buy')

    def sell(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        return self._post_send_order(price, qty, order_type, 'sell')


    def cancel(self, oid):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/{order}"
        url = url.format(venue=self.venue, stock=self.stock, order=oid)
        return self._delete(url)


    """
        API calls to get order status. Currently not used as the websocket seems to be providing
            similar results faster.
    """
    def get_order_status(self, oid):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/{oid}".format(venue=self.venue, stock=self.stock, oid=oid)
        res = self._get_response(url)
        if res.get('ok'):
            return res
        else:
            raise Exception('Didnt get proper data from get_order_status')

    def get_all_orders_in_stock(self):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/accounts/{account}/stocks/{stock}/orders".format(venue=self.venue, stock=self.stock, account=self.account)
        res = self._get_response(url)
        if res.get('ok'):
            return res.get('orders')
        else:
            raise Exception('Didnt get proper data from get_all_orders_in_stock')

    def get_all_orders(self):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/accounts/{account}/orders".format(venue=self.venue, account=self.account)
        res = self._get_response(url)
        if res.get('ok'):
            return res.get('orders')
        else:
            raise Exception('Didnt get proper data from get_all_orders')


