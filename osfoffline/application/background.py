import logging
import threading

from urllib.request import urlopen
from urllib.error import URLError

from osfoffline.sync.local import LocalSyncWorker
from osfoffline.sync.remote import RemoteSyncWorker
from osfoffline.tasks import Intervention, Notification
from osfoffline.tasks.queue import OperationWorker
from osfoffline.utils import Singleton
from osfoffline.utils.internetchecker import check_internet
from osfoffline.utils.internetchecker import require_internet


logger = logging.getLogger(__name__)

def check_internet():
    try:
        urlopen('http://www.google.com')
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


class BackgroundHandler(metaclass=Singleton):

    def set_intervention_cb(self, cb):
        Intervention().set_callback(cb)

    def set_notification_cb(self, cb):
        Notification().set_callback(cb)

    def start(self):
        # Avoid blocking the UI thread, Remote Sync initialization can request user intervention.
        threading.Thread(target=self._start).start()

    def sync_now(self):
        # Avoid blocking the UI thread, will block if the internet is down
        threading.Thread(target=self._sync_now).start()

    def _start(self):
        require_internet()
        OperationWorker().start()
        RemoteSyncWorker().initialize()
        RemoteSyncWorker().start()
        LocalSyncWorker().start()

    def _sync_now(self):
        if not check_internet():
            self.stop()
            require_internet()
        RemoteSyncWorker().sync_now()

    def stop(self):
        RemoteSyncWorker().stop()
        OperationWorker().stop()
        LocalSyncWorker().stop()

        del type(OperationWorker)._instances[OperationWorker]
        del type(RemoteSyncWorker)._instances[RemoteSyncWorker]
        del type(LocalSyncWorker)._instances[LocalSyncWorker]
