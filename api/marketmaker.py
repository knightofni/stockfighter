import json
import random
import time

import requests
import websocket
import pandas as pd

from stockfighter import config

API_KEY = config.get('api', 'API_KEY')

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
        self.url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders"
        # Creates a websocket connection
        self.wsurl = 'wss://api.stockfighter.io/ob/api/ws/{account}/venues/{venue}/tickertape/stocks/{stock}'
        self.wsurl.format(account=self.account, venue=self.venue, stock=self.stock)
        self.wsq = websocket.WebSocket().connect(url)


    def _get_response(self, url):
        r = requests.get(url, header=self.header)
        return r.json()

    def quote_ws(self):
        """
            Polls websocket for quote information
        """
        result =  json.loads(self.wsq.recv())
        if result.get('ok'):
            # we got proper data
            quote = result.get('quote')
            self.quote = quote
            return quote
        else:
            print('Error when trying to get quote from websocket')

    def completion(self):
        """
            Updates GameMaster so that we know what is the current trading day
        """
        self.gm._update()
        if self.gm.live:
            print('{}/{} trading days'.format(self.gm.tradingDay, self.gm.endOfTheWorldDay))


    def buy_limit(self, price, qty):
        url = self.url.format(venue=self.venue, stock=self.stock)
        order = {
            'account'  : self.account,
            'venue'    : self.venue,
            'stock'    : self.stock,
            'price'    : price,
            'qty'      : qty,
            'direction':'buy',
            'orderType':'limit'
        }
        res = requests.post(url, data=json.dumps(order), headers=self.headers)
        return res.json()

    def order_book(self):
        return self.sft.order_book(self.stock)

    def quote(self):
        return self.sft.get_quote(self.stock)

    def order_status(self, oid):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/:{oid}".format(venue=self.venue, stock=self.stock, oid=oid)
        res = self._get_response(url)
        return res.json()


