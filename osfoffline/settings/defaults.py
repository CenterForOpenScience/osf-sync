import os

from appdirs import user_data_dir
from appdirs import user_log_dir


# General settings
PROJECT_NAME = 'osf-offline'
PROJECT_AUTHOR = 'cos'
APPLICATION_SCOPES = 'osf.full_write'

# Base URL for API server; used to fetch data
OSF_URL = 'https://test.osf.io'
API_BASE = 'https://test-api.osf.io'
FILE_BASE = 'https://test-files.osf.io'

# Interval (in seconds) to poll the OSF for server-side file changes
REMOTE_CHECK_INTERVAL = 60 * 5  # Every 5 minutes

# Time to keep alert messages on screen (in milliseconds); may not be configurable on all platforms
ALERT_TIME = 1000  # ms

LOG_LEVEL = 'INFO'

# Logging configuration
FILE_FORMATTER = '[%(asctime)s][%(threadName)s][%(filename)s][%(levelname)s][%(name)s]: %(message)s'

IGNORED_NAMES = ['.DS_Store', 'lost+found', 'Desktop.ini']
IGNORED_PATTERNS = ['*.DS_Store', '*lost+found', '*Desktop.ini']

OSF_STORAGE_FOLDER = 'OSF Storage'

LOCAL_DELETE_THRESHOLD = 10

# wab~,vmc,vhd,vo1,vo2,vsv,vud,vmdk,vmsn,vmsd,hdd,vdi,vmwarevm,nvram,vmx,vmem,iso,dmg,sparseimage,wim,ost,o,qtch,log
# wab~,vmc,vhd,vdi,vo1,vo2,vsv,vud,iso,dmg,sparseimage,sys,cab,exe,msi,dll,dl_,wim,ost,o,qtch,log,ithmb,vmdk,vmem,vmsd,vmsn,vmss,vmx,vmxf,menudata,appicon,appinfo,pva,pvs,pvi,pvm,fdd,hds,drk,mem,nvram,hdd

# Variables used to control where application config data is stored
PROJECT_DB_DIR = user_data_dir(appname=PROJECT_NAME, appauthor=PROJECT_AUTHOR)
PROJECT_DB_FILE = os.path.join(PROJECT_DB_DIR, 'osf.db')

PROJECT_LOG_DIR = user_log_dir(appname=PROJECT_NAME, appauthor=PROJECT_AUTHOR)
PROJECT_LOG_FILE = os.path.join(PROJECT_LOG_DIR, 'osfoffline.log')

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
        'handlers': ['console', 'logfile']
    }
}
