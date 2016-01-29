import logging
import threading
import urllib


from . import Singleton


logger = logging.getLogger(__name__)


class InternetChecker(threading.Thread, metaclass=Singleton):

    def __init__(self):
        super().__init__()
        self.__stop = threading.Event()
        self.has_connection = False

    def run(self):
        while not self.__stop.is_set():
            try:
                urllib.urlopen("http://www.google.com")
            except urllib.URLError:
                logger.infoe('Internet is down')
            else:
                logger.info("Internet is up and running.")
                has_connection = True
            return has_connection

