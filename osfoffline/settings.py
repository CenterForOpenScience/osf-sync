import logging
import logging.config
import os

from appdirs import user_config_dir, user_data_dir

## Development mode: use a local OSF dev version and more granular logging
DEV_MODE = False  # TODO (abought): auto-set flag when using `inv start_for_tests`

### General settings
PROJECT_NAME = 'osf-offline'
PROJECT_AUTHOR = 'cos'

### Variables used to control where application config data is stored
PROJECT_CONFIG_PATH = user_config_dir(appname=PROJECT_NAME, appauthor=PROJECT_AUTHOR)
PROJECT_DB_PATH = user_data_dir(appname=PROJECT_NAME, appauthor=PROJECT_AUTHOR)
DB_FILE_PATH = os.path.join(PROJECT_DB_PATH, 'osf.db')

### Base URL for API server; used to fetch data
# API_BASE = 'http://localhost:5000'
if DEV_MODE is True:
    API_BASE = 'http://localhost:8000'
    FILE_BASE = 'http://localhost:7777'  ## FIXME: Dev mode currently does not work with local waterbutler (abought)
else:
    API_BASE = 'https://staging-api.osf.io'
    FILE_BASE = 'https://staging-files.osf.io'

### Interval (in seconds) to poll the OSF for server-side file changes
if DEV_MODE is True:
    POLL_DELAY = 5  # seconds
else:
    POLL_DELAY = 10 * 60  # seconds

### Time to keep alert messages on screen (in milliseconds); may not be configurable on all platforms
ALERT_TIME = 1000  # ms


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
        }
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
        'handlers': ['console']
    }
}

logging_config = DEFAULT_LOGGING_CONFIG
logging.config.dictConfig(logging_config)


## TODO: Add a custom excepthook and implement logging to a file on user's hard drive (after cleanup PR)
## logger.critical('Whatever', exc_info=(exc_type, exc_value, tb))
