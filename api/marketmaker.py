import json
import random
import time

import requests
import websocket
import pandas as pd

from stockfighter import config
from .websockets import WebSocketListenerQuotes

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
            - Will automatically
    """
    ORDER_TYPE = ('limit', 'market', 'fill-or-kill', 'immediate-or-cancel')
    def __init__(self, gm):
        # Extracts info from gamemaster
        self.gm = gm
        self.venue = gm.venues[0]
        self.stock = gm.tickers[0]
        self.account = gm.account
        # Instanciate a StockFighterTrade. Checks health of sf
        self.sft = StockFighterTrader(self.venue)
        # Genetic API data
        self.headers = {
            'X-Starfighter-Authorization' : API_KEY
        }
        order_url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders"
        self.order_url = order_url.format(venue=self.venue, stock=self.stock)

        # Start a websocket listener for quotes
        self.wsq = WebSocketListenerQuotes(self)
        # # Creates a websocket connection for fills
        # self.wsurl_f = 'wss://api.stockfighter.io/ob/api/ws/{account}/venues/{venue}/executions/stocks/{stock}'
        # self.wsurl_f = self.wsurl_f.format(account=self.account, venue=self.venue, stock=self.stock)
        print('Market Maker initiated')


    def _get_response(self, url):
        r = requests.get(url, header=self.header)
        return r.json()

    def _post_json(self, url, data):
        res = requests.post(url, data=json.dumps(data), headers=self.headers)
        return res.json()

    def get_histo(self):
        return self.wsq.get_data()

    def completion(self):
        """
            Updates GameMaster so that we know what is the current trading day
        """
        self.gm._update()
        if self.gm.live:
            print('{}/{} trading days'.format(self.gm.tradingDay, self.gm.endOfTheWorldDay))

    def _get_basic_order_dict(price, qty):
        order = {
        'account'  : self.account,
        'venue'    : self.venue,
        'stock'    : self.stock,
        'price'    : price,
        'qty'      : qty,
        }

        return order

    def _send_order(self, price, qty, order_type, direction):
        if order_type not in self.ORDER_TYPE:
            raise Exception('order_type must be on of : [{}]'.format(', '.join(self.ORDER_TYPE)))

        order = self._get_basic_order_dict(price, qty)
        order['direction'] = direction
        order['orderType'] = order_type
        res = self._post_json(self.order_url, order)
        return res.json()

    def buy(self, price, qty, order_type='limit'):
        return self._send_order(price, qty, order_type, 'buy')

    def sell(self, price, qty, order_type='limit'):
        return self._send_order(price, qty, order_type, 'sell')


    def order_book(self):
        return self.sft.order_book(self.stock)

    def quote(self):
        return self.sft.get_quote(self.stock)

    def order_status(self, oid):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/:{oid}".format(venue=self.venue, stock=self.stock, oid=oid)
        res = self._get_response(url)
        return res.json()


