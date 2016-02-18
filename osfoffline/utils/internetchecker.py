import logging
import time

from urllib.request import urlopen
from urllib.error import URLError


logger = logging.getLogger(__name__)


def check_internet():
    try:
        urlopen('http://www.google.com')
        logger.info('Internet is up and running.')
        return True
    except URLError:
        logger.warning('No internet connection')
        return False


def require_internet():
    backoff = 5
    while not check_internet():
        if backoff < 60:
            backoff += 5
        time.sleep(backoff)
