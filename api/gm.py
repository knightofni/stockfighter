import requests
import json

from stockfighter import config

API_KEY = config.get('api', 'APIKEY')

class GameMaster(object):
    """
        Starts / Restarts sessions
        Keeps game info and feeds it to further objects
        from : https://discuss.starfighters.io/t/the-gm-api-how-to-start-stop-restart-resume-trading-levels-automagically/143/2
    """
    URL = 'https://www.stockfighter.io/gm'
    LEVELS = ['first_steps', 'chock_a_block']

    def __init__(self):

        self.headers = {
            'Cookie' : 'api_key={}'.format(API_KEY)
            }

    def _update(self):
        url = self.URL + '/instances/{instanceId}'.format(instanceId=self.instanceId)
        resp = self._get(url)
        self.live = resp.get('ok')
        self.endOfTheWorldDay = resp.get('details').get('endOfTheWorldDay')
        self.tradingDay = resp.get('details').get('tradingDay')


    def _post(self, url):
        r = requests.post(url, headers=self.headers)
        return r.json()

    def _get(self, url):
        r = requests.get(url, headers=self.headers)
        return r.json()

    def start(self, level):
        if level not in self.LEVELS:
            raise Exception('Available levels are : {}'.fornat(self.LEVELS))

        url = self.URL + '/levels/{level}'.format(level=level)
        resp = self._post(url)
        self.account = resp.get('account')
        self.instanceId = resp.get('instanceId')
        self.tickers = resp.get('tickers')
        self.venues = resp.get('venues')
        self.start_resp = resp
        print('GameMaster : level {} initiated'.format(level))

    def restart(self):
        url = self.URL + '/instances/{instanceId}/restart'.format(instanceId=self.instanceId)
        resp = self._post(url)
        print('Restarted')
