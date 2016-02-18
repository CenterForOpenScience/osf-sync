import logging
import threading
import time

from urllib.request import urlopen
from urllib.error import URLError

from . import Singleton

from osfoffline import settings
from osfoffline.sync.remote import RemoteSyncWorker


logger = logging.getLogger(__name__)


class InternetChecker(threading.Thread, metaclass=Singleton):

    def __init__(self):
        super().__init__()
        self.__stop = threading.Event()
        self.has_connection = False

    def run(self):
        while not self.has_connection:
            time.sleep(settings.INTERNET_CHECK_INTERVAL)
            self.check_internet()

    def check_internet(self):
        try:
            urlopen("http://www.google.com")
        except URLError:
            logger.info('Internet is down')
            self.has_connection = False
            if RemoteSyncWorker():
                RemoteSyncWorker().stop()
                del type(RemoteSyncWorker)._instances[RemoteSyncWorker]
        else:
            logger.info("Internet is up and running.")
            self.has_connection = True
            self.stop()
        return self.has_connection

    def stop(self):
        logger.info('Stopping InternetChecker')
        self.__stop.set()

        if not RemoteSyncWorker().is_alive():
            RemoteSyncWorker().initialize()
            RemoteSyncWorker().start()
        else:
            RemoteSyncWorker().sync_now()

        del type(InternetChecker)._instances[InternetChecker]
