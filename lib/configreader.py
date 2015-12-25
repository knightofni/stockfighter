import configparser
import os

from stockfighter import BASE_PATH

config_fname = 'lib/config.ini'
config_path = os.path.join(BASE_PATH, config_fname)
config = None

def ensure_config_is_read():
    global config
    if not config:
        config = configparser.ConfigParser()
        if os.path.isfile(config_path):
            config.read(config_path)
        else:
            raise Exception('no config file at {}. Aborting.'.format(config_path))


ensure_config_is_read()
