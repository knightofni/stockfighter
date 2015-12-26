import websocket
import arrow
import json
import threading
import pandas as pd


class ThreadedWebSocket(object):
    """
        - Creates a websocket listener
        - Runs it into a thread
        - Create child class. The __init__ method of the child must send the url of the websocket
            to the parent's __init__ method
    """
    def __init__(self, url):
        self._create_thread(url)

    def _create_thread(self, url):
        ws = websocket.WebSocketApp(url, on_message = self.on_message, on_close = self.on_close)
        ws.data = []
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        self.ws = ws

    @staticmethod
    def on_message(ws, message):
        ws.data.append(json.loads(message))

    @staticmethod
    def on_close(ws):
        print("### closed ###")

class WebSocketListenerQuotes(ThreadedWebSocket):
    """
        - Creates a websocket listener
        - Runs it into a thread
    """
    def __init__(self, mm):
        url ='wss://api.stockfighter.io/ob/api/ws/{account}/venues/{venue}/tickertape/stocks/{stock}'
        url = url.format(account=mm.account, venue=mm.venue, stock=mm.stock)
        ThreadedWebSocket.__init__(self, url)

    @staticmethod
    def _update_spread_data(histo_data, quote):
        histo_data['quoteTime'].append(arrow.get(quote.get('quoteTime')).datetime)
        histo_data['ask'].append(quote.get('ask'))
        histo_data['askSize'].append(quote.get('askSize'))
        histo_data['bid'].append(quote.get('bid'))
        histo_data['bidSize'].append(quote.get('bidSize'))
        return histo_data

    def get_spread(self):
        histo_data = {
            'quoteTime' : [],
            'ask'  : [],
            'askSize'  : [],
            'bid' : [],
            'bidSize' : [],
        }

        for item in self.ws.data:
            if item.get('ok'):
                histo_data = self._update_spread_data(histo_data, item.get('quote'))

        df = pd.DataFrame.from_dict(histo_data).set_index('quoteTime').drop_duplicates()
        df['spread'] = df['ask'] - df['bid']
        return df.dropna(subset=['spread'])

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
    def __init__(self, mm):
        url = 'wss://api.stockfighter.io/ob/api/ws/{account}/venues/{venue}/executions/stocks/{stock}'
        url = url.format(account=mm.account, venue=mm.venue, stock=mm.stock)
        ThreadedWebSocket.__init__(self, url)




