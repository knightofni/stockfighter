import json
import time
import threading

import requests

from stockfighter import config
from .venue import StockFighterTrader
from .websockets import WebSocketListenerQuotes, WebSocketListenerFills

API_KEY = config.get('api', 'APIKEY')

class MarketBroker(object):
    """
        Main API.
            - Needs an instance of GameMaster to be instanciated
            - MarketMaker expects that the GameMaster instance has already started a level

        Public Methods / Attributes:
            - order_book                : dict. Current Bid Ask on the stock
            - all_orders_in_stock       : list of dicts. All the orders of our account in the stock
            - get_spread()              : method, returning DataFame. Historical Bid / Ask
            - get_latest_quote_time()   : method, returning arrow time.  of the latest quote.
            - get_quote()               : method, returning DataFame. Timeserie of trades

        Private Methods :
            - _buy / _sell / _cancel / _post_send_order     : order management
            -

    """
    _ORDER_TYPE = ('limit', 'market', 'fill-or-kill', 'immediate-or-cancel')

    def __init__(self, gm=None, update=3):
        # Extracts info from gamemaster
        if gm and gm.ready:
            self._gm = gm
            self._venue = gm.venues[0]
            self._stock = gm.tickers[0]
            self._account = gm.account
            self._db = gm._db
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
        self.__order_url = order_url.format(venue=self._venue, stock=self._stock)

        # Start a websocket listener for quotes
        self._wsq = WebSocketListenerQuotes(self)
        # # Creates a websocket connection for fills
        self._wsf = WebSocketListenerFills(self)

        # Starts polling loop
        self.all_orders_in_stock = dict()
        self.__update = update
        thrd = threading.Thread(target=self.__loop)
        thrd.daemon=True
        thrd.start()

        print('Market Maker for stock {} initiated'.format(self._stock))


    """
        Standard API helpers
    """
    def __get_response(self, url):
        res = requests.get(url, headers=self._headers)
        return res.json()

    def __post_json(self, url, data):
        res = requests.post(url, data=json.dumps(data), headers=self._headers)
        return res.json()

    def __delete(self, url):
        res = requests.delete(url, headers=self._headers)
        return res.json()

    def __check_websocket_quotes_health(self):
        if not self._wsq.ws.live:
            data = self._wsq.ws.data.copy()
            self._wsq = WebSocketListenerQuotes(self, data)
            print('WebSocketListenerQuotes restarted')

    def __check_websocket_fills_health(self):
        if not self._wsf.ws.live:
            data = self._wsf.ws.data.copy()
            self._wsf = WebSocketListenerFills(self, data)
            print('WebSocketListenerFills restarted')

    """
        Market Data
    """
    def get_histo(self):
        self.__check_websocket_quotes_health()
        return self._wsq.get_data()

    def get_spread(self, rows='all'):
        self.__check_websocket_quotes_health()
        return self._wsq.get_spread(rows=rows)

    @property
    def order_book(self):
        return self._sft.order_book

    # def quote(self):  ## Still usefull ??
    #     return self._sft.get_quote(self._stock)

    def _get_fills_ws(self):
        # Data from the Fills websocket
        self.__check_websocket_fills_health()
        return self._wsf.ws.data

    def get_latest_quote_time(self):
        # arrow time of the latest quote
        self.__check_websocket_quotes_health()
        return self._wsq.get_latest_quote_time()

    def current_quote(self):
        # Get data on the latest quote
        return self._wsq.get_quote()

    """
        Sends buy / sell orders
            - Will parse and store the execution result
            - can also cancel orders
    """

    def __post_send_order(self, qty, price, order_type, direction):
        if order_type not in self._ORDER_TYPE:
            raise Exception('order_type must be on of : [{}]'.format(', '.join(self._ORDER_TYPE)))

        if order_type != 'market' and not price:
            raise Exception('need a price for order_type {}'.format(order_type))


        order = {
            'account'  : self._account,
            'venue'    : self._venue,
            'stock'    : self._stock,
            'price'    : int(price),
            'qty'      : int(qty),
            'direction' : direction,
            'orderType' : order_type,
        }

        if qty > 0:
            res = self.__post_json(self.__order_url, order)
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
        return self.__post_send_order(qty, price, order_type, 'buy')

    def _sell(self, qty, price=None, order_type='limit'):
        """
            Buy this MarketMaker's stock
            input :
                qty     : int, how many shares you want to buy
                price   : int, price x 100
                order_type : string, limit, market, fill-or-kill, immediate-or-cancel
        """
        return self.__post_send_order(qty, price, order_type, 'sell')


    def _cancel(self, oid):
        """
            Cancels order of id `oid`.
            Adds the execution result to self.closedorders
        """
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/{order}"
        url = url.format(venue=self._venue, stock=self._stock, order=oid)
        res = self.__delete(url)
        return res


    """
        API calls to get order status. Currently not used as the websocket seems to be providing
            similar results faster.
    """
    def __loop(self):
        self.all_orders_in_stock = None
        while True:
            self.all_orders_in_stock = self._get_all_orders_in_stock()
            time.sleep(self.__update)

    def _get_order_status(self, oid):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/orders/{oid}".format(venue=self._venue, stock=self._stock, oid=oid)
        res = self.__get_response(url)
        if res.get('ok'):
            return res
        else:
            raise Exception('Didnt get proper data from get_order_status')

    def _get_all_orders_in_stock(self):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/accounts/{account}/stocks/{stock}/orders".format(venue=self._venue, stock=self._stock, account=self._account)
        res = self.__get_response(url)
        if res.get('ok'):
            return res.get('orders')
        else:
            raise Exception('Didnt get proper data from get_all_orders_in_stock')

    def _get_all_orders(self):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/accounts/{account}/orders".format(venue=self._venue, account=self._account)
        res = self.__get_response(url)
        if res.get('ok'):
            return res.get('orders')
        else:
            raise Exception('Didnt get proper data from get_all_orders')


