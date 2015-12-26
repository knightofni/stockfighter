import json
import shelve
import os
from contextlib import closing

import requests

from stockfighter import config
from stockfighter import BASE_PATH

API_KEY = config.get('api', 'APIKEY')


class GameMaster(object):
    """
        Starts / Restarts sessions
        Keeps game info and feeds it to further objects
        from : https://discuss.starfighters.io/t/the-gm-api-how-to-start-stop-restart-resume-trading-levels-automagically/143/2

        Public Methods :
            - start     : arg : level, string identifying the level. Must be part of _LEVELS class attribute
            - stop      : stop a level
            - restart   : restart a level with same stock / venue
            - completion : Updates level state. Prints completion (number of days in game). Usefull to get extra data

    """
    _URL = 'https://www.stockfighter.io/gm'
    _LEVELS = ['first_steps', 'chock_a_block', 'sell_side']

    def __init__(self):
        self._shelve_path = os.path.join(BASE_PATH, 'lib/gm.db')
        self.headers = {
            'Cookie' : 'api_key={}'.format(API_KEY)
            }
        self._instanceId = self._load_instance_id()

        if self._instanceId:
            # try to resume
            self.resume()

        ## setting up level info
        self.target_price_l2 = None



    """
        API helpers
    """
    def _post(self, url):
        r = requests.post(url, headers=self.headers)
        return r.json()

    def _get(self, url):
        r = requests.get(url, headers=self.headers)
        return r.json()

    """
        Saving and Loading the instanceId to disk for easier resume
    """
    def _save_instance_id(self, instanceId):
        with closing(shelve.open(self._shelve_path)) as db:
            db['instanceId'] = instanceId

    def _load_instance_id(self):
        with closing(shelve.open(self._shelve_path)) as db:
            instanceId = db.get('instanceId')

        return instanceId

    """
        Updating the GameMaster to know advancement / get extra data
    """
    def completion(self):
        """
            Updates GameMaster so that we know what is the current trading day
        """
        self._update()
        if self._live:
            print('{}/{} trading days'.format(self._tradingDay, self._endOfTheWorldDay))
        else:
            print('Game closed')

    def _flash_level2(self):
        """
            Parses the flash message for level 2 (it includes the target price)
        """
        flash = self._status.get('flash', {}).get('info')
        if flash:
            i1 = flash.index('$')
            i2 = flash[i1+1:].index('$')
            self.target_price_l2 = float(flash[i1+i2+2:-1])
        else:
            self.target_price_l2 = None


    def _update(self):
        url = self._URL + '/instances/{instanceId}'.format(instanceId=self._instanceId)
        resp = self._get(url)
        self._live = resp.get('ok')
        self._endOfTheWorldDay = resp.get('details').get('endOfTheWorldDay')
        self._tradingDay = resp.get('details').get('tradingDay')
        self._status = resp
        self._flash_level2()


    """
        Controls the GameMaster
    """
    def _parse_starting_info(self, resp):
        if resp.get('ok'):
            self.account = resp.get('account')
            self._instanceId = resp.get('instanceId')
            self.tickers = resp.get('tickers')
            self.venues = resp.get('venues')
            self._start_resp = resp
            self.target_price_l2 = None
            ret_val = True
        else:
            print('Error : {}'.format(resp.get('error')))
            ret_val = False

        return ret_val

    def start(self, level):
        if level not in self._LEVELS:
            raise Exception('Available levels are : {}'.fornat(self._LEVELS))

        url = self._URL + '/levels/{level}'.format(level=level)
        resp = self._post(url)
        if self._parse_starting_info(resp):
            self._save_instance_id(self._instanceId)
            print('GameMaster : level {} initiated'.format(level))

    def stop(self):
        if self._instanceId is not None:
            url = self._URL + '/instances/{instanceId}/stop'.format(instanceId=self._instanceId)
            resp = self._post(url)
            print('Stopped')
        else:
            raise Exception('Cant stop because there is no recorded instanceId')

    def restart(self):
        if self._instanceId is not None:
            url = self._URL + '/instances/{instanceId}/restart'.format(instanceId=self._instanceId)
            resp = self._post(url)
            if self._parse_starting_info(resp):
                print('Restarted')
        else:
            raise Exception('Cant restart because there is no recorded instanceId')

    def resume(self):
        if self._instanceId is not None:
            url = self._URL + '/instances/{instanceId}/resume'.format(instanceId=self._instanceId)
            resp = self._post(url)
            if self._parse_starting_info(resp):
                print('Resumed')
        else:
            raise Exception('Cant resume because there is no recorded instanceId')
