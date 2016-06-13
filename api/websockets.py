import json
import threading

import websocket
import arrow
import pandas as pd


class ThreadedWebSocket(object):
    """
        - Creates a websocket listener
        - Runs it into a thread
        - Create child class. The __init__ method of the child must send the url of the websocket
            to the parent's __init__ method
    """
    def __init__(self, url, data):
        self._create_thread(url, data)

    def _create_thread(self, url, data):
        webs = websocket.WebSocketApp(url, on_message = self.on_message, on_close = self.on_close)
        webs.data = []
        wst = threading.Thread(target=webs.run_forever)
        wst.daemon = True
        wst.start()
        self.webs = webs
        self.webs.live = True

    @staticmethod
    def on_message(webs, message):
        webs.data.append(json.loads(message))

    @staticmethod
    def on_close(webs):
        webs.live = False
        print("### closed ###")


class WebSocketListenerQuotes(ThreadedWebSocket):
    """
        Public methods :
            - get_latest_quote_time : datetime of the latest quote
            - get_spread            : dataframe (timeserie) of the bid / ask.
                                    removes dates where we have only bids or asks
            - get_data              : dataframe (timeserie) of trades.
    """
    def __init__(self, mm, data=None):
        if data is None:
            data = []

        url = 'wss://api.stockfighter.io/ob/api/ws/{account}/venues/{venue}/tickertape/stocks/{stock}'
        url = url.format(account=mm._account, venue=mm._venue, stock=mm._stock)
        ThreadedWebSocket.__init__(self, url, data)

    def get_latest_quote_time(self):
        if len(self.webs.data) > 0:
            return arrow.get(self.webs.data[-1].get('quote').get('quoteTime'))
        else:
            return arrow.utcnow()

    def get_quote(self):
        if len(self.webs.data) > 1:
            quote = self.webs.data[-1]
            if quote.get('ok'):
                return quote.get('quote')
            else:
                return None

    @staticmethod
    def _update_spread_data(histo_data, quote):
        histo_data['quoteTime'].append(arrow.get(quote.get('quoteTime')).datetime)
        histo_data['ask'].append(quote.get('ask'))
        histo_data['askSize'].append(quote.get('askSize'))
        histo_data['bid'].append(quote.get('bid'))
        histo_data['bidSize'].append(quote.get('bidSize'))
        return histo_data

    def get_spread(self, rows='all'):
        histo_data = {
            'quoteTime' : [],
            'ask'  : [],
            'askSize'  : [],
            'bid' : [],
            'bidSize' : [],
        }

        for item in reversed(self.webs.data):
            if item.get('ok'):
                histo_data = self._update_spread_data(histo_data, item.get('quote'))
            if rows != 'all' and len(histo_data.get('quoteTime')) >  rows:
                break

        df = pd.DataFrame.from_dict(histo_data).set_index('quoteTime').drop_duplicates()
        df['spread'] = df['ask'] - df['bid']
        df.sort_index()
        return df#.dropna(subset=['spread'])

    @staticmethod
    def _update_histo_data(histo_data, quote):
        histo_data['lastTrade'].append(arrow.get(quote.get('lastTrade')).datetime)
        histo_data['last'].append(quote.get('last'))
        histo_data['lastSize'].append(quote.get('lastSize'))
        return histo_data

    def get_data(self):
        histo_data = {
            'lastTrade' : [],
            'last'  : [],
            'lastSize'  : [],
        }

        for item in self.ws.data:
            if item.get('ok'):
                histo_data = self._update_histo_data(histo_data, item.get('quote'))

        return pd.DataFrame.from_dict(histo_data).set_index('lastTrade').drop_duplicates()


class WebSocketListenerFills(ThreadedWebSocket):
    """
        - Creates a websocket listener
        - Runs it into a thread
    """
    def __init__(self, mm, data=None):
        if data is None:
            data = []

        url = 'wss://api.stockfighter.io/ob/api/ws/{account}/venues/{venue}/executions/stocks/{stock}'
        url = url.format(account=mm._account, venue=mm._venue, stock=mm._stock)
        ThreadedWebSocket.__init__(self, url, data)




