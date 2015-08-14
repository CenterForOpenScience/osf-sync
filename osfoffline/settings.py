import os
import json
import logging
import logging.config
from appdirs import user_config_dir, user_data_dir
import furl
PROJECT_NAME = 'osf-offline'
PROJECT_AUTHOR = 'cos'
PROJECT_CONFIG_PATH = user_config_dir(PROJECT_NAME, PROJECT_AUTHOR)
PROJECT_DB_PATH = user_data_dir(PROJECT_NAME, PROJECT_AUTHOR)

API_BASE = 'http://localhost:8000'
WB_BASE = 'http://localhost:7777'

# API_BASE = 'https://staging2.osf.io/api/'
# WB_BASE = 'https://staging2-files.osf.io'



# import hashlib
#
# try:
#     from waterbutler import settings
# except ImportError:
#     settings = {}
#
# config = settings.get('SERVER_CONFIG', {})
#
#
# ADDRESS = config.get('ADDRESS', '127.0.0.1')
# PORT = config.get('PORT', 7777)
#
# DEBUG = config.get('DEBUG', True)
#
# CHUNK_SIZE = config.get('CHUNK_SIZE', 65536)  # 64KB
# MAX_BODY_SIZE = config.get('MAX_BODY_SIZE', int(4.9 * (1024 ** 3)))  # 4.9 GB


# try:
#
#     DEFAULT_FORMATTER = {
#         '()': 'colorlog.ColoredFormatter',
#         'format': '%(cyan)s[%(asctime)s]%(log_color)s[%(levelname)s][%(name)s]: %(reset)s%(message)s'
#     }
# except ImportError:
#     DEFAULT_FORMATTER = {
#         '()': 'waterbutler.core.logging.MaskFormatter',
#         'format': '[%(asctime)s][%(levelname)s][%(name)s]: %(message)s',
#         'pattern': '(?<=cookie=)(.*?)(?=&|$)',
#         'mask': '***'
#     }
import colorlog  # noqa
DEFAULT_FORMATTER = {
   '()': 'colorlog.ColoredFormatter',
   'format': '%(cyan)s[%(asctime)s]%(log_color)s[%(threadName)s][%(filename)s][%(levelname)s][%(name)s]: %(reset)s%(message)s'
}


DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': DEFAULT_FORMATTER,
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'console'
        },
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'level': 'INFO'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}



# try:
#     config_path = os.environ['{}_CONFIG'.format(PROJECT_NAME.upper())]
# except KeyError:
#     env = os.environ.get('ENV', 'test')
#     config_path = '{}/{}-{}.json'.format(PROJECT_CONFIG_PATH, PROJECT_NAME, env)
#
#
# config = {}
# config_path = os.path.expanduser(config_path)
# if not os.path.exists(config_path):
#     logging.warning('No \'{}\' configuration file found'.format(config_path))
# else:
#     with open(os.path.expanduser(config_path)) as fp:
#         config = json.load(fp)
#
#
# def get(key, default):
#     return config.get(key, default)


# logging_config = get('LOGGING', DEFAULT_LOGGING_CONFIG)
logging_config = DEFAULT_LOGGING_CONFIG
logging.config.dictConfig(logging_config)