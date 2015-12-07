import logging
import logging.config

# Must import in order to be included by PyInstaller
import raven  # noqa

from osfoffline.settings.defaults import *  # noqa


logger = logging.getLogger(__name__)

try:
    from osfoffline.settings.local import *  # noqa
except ImportError:
    logger.warning('No local.py found. Using default settings.')

# Ensure that storage directories are created when application starts
for path in (PROJECT_DB_DIR, PROJECT_LOG_DIR):
    logger.info('Ensuring {} exists'.format(path))
    os.makedirs(path, exist_ok=True)


# Define logging configuration to use individual override params from settings files
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {'format': FILE_FORMATTER},
        'file_log': {'format': FILE_FORMATTER}
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOG_LEVEL,
            'formatter': 'console'
        },
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'level': LOG_LEVEL
        },
        'logfile': {
            'class': 'logging.FileHandler',
            'level': LOG_LEVEL,
            'filename': PROJECT_LOG_FILE,
            'formatter': 'file_log'
        },
        'sentry': {
            'level': 'ERROR',  # Don't fill server with debug messages
            'class': 'raven.handlers.logging.SentryHandler',
            'dsn': SENTRY_DSN,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False
        }
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console', 'logfile', 'sentry']
    }
}

# Log to both local file and Raven server
logging.config.dictConfig(LOGGING_CONFIG)
