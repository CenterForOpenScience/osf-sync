import logging
import logging.config
import os
import sys

from appdirs import user_log_dir

from .app_settings import DEV_MODE, PROJECT_NAME, PROJECT_AUTHOR

PROJECT_LOG_PATH = user_log_dir(appname=PROJECT_NAME, appauthor=PROJECT_AUTHOR)
LOG_FILE_PATH = os.path.join(PROJECT_LOG_PATH, 'osfoffline.log')


### Logging configuration
DEFAULT_FORMATTER = {
    '()': 'colorlog.ColoredFormatter',
    'format': '%(cyan)s[%(asctime)s]%(log_color)s[%(threadName)s][%(filename)s][%(levelname)s][%(name)s]: %(reset)s%(message)s'
}

if DEV_MODE is True:
    log_level = 'DEBUG'
else:
    log_level = 'INFO'


DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': DEFAULT_FORMATTER,
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'console'
        },
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'level': log_level
        },
        'logfile': {
            'class': 'logging.FileHandler',
            'level': log_level,
            'filename': LOG_FILE_PATH
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': log_level,
            'propagate': False
        }
    },
    'root': {
        'level': log_level,
        'handlers': ['console', 'logfile']
    }
}

logging_config = DEFAULT_LOGGING_CONFIG
logging.config.dictConfig(logging_config)


def capture_exceptions(exc_type, exc_value, tb):
    """Ensure that uncaught exceptions are logged"""
    logging.exception('Fatal error: ', exc_info=(exc_type, exc_value, tb))

sys.excepthook = capture_exceptions
