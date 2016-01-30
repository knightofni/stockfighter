import requests
import threading
import time

class StockFighterTrader(object):
    """
        - Checks health of API on construction
        - Used for API calls that do not need authentication
        - Polls the order book by default every 3 seconds
    """

    def __init__(self, venue, stock, update=3):
        self.venue = venue
        if not self._isonline():
            raise Exception('Stockfighter not online')
        if not self._venue_online(venue):
            raise Exception('Venue {} not online'.format(venue))

        self._stock = stock
        self.order_book = None
        self._update = update
        thrd = threading.Thread(target=self._loop)
        thrd.start()

        print('StockFighterTrader initiated')

    def _loop(self):
        while True:
            self.order_book = self._order_book(self._stock)
            time.sleep(self._update)


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

    def _get_quote(self, ticker):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}/quote".format(venue=self.venue, stock=ticker)
        res = self._get_response(url)
        return res

    def _order_book(self, ticker):
        url = "https://api.stockfighter.io/ob/api/venues/{venue}/stocks/{stock}".format(venue=self.venue, stock=ticker)
        res = self._get_response(url)
        return res


