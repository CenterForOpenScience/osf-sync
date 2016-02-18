import logging
import threading

from urllib.request import urlopen
from urllib.error import URLError

from osfoffline.sync.local import LocalSyncWorker
from osfoffline.sync.remote import RemoteSyncWorker
from osfoffline.tasks import Intervention, Notification
from osfoffline.tasks.queue import OperationWorker
from osfoffline.utils import Singleton
from osfoffline.utils.internetchecker import InternetChecker


logger = logging.getLogger(__name__)


def check_connection():
    try:
        urlopen("http://www.google.com")
    except URLError:
        Notification().info('Internet is down')
        if not InternetChecker():
            InternetChecker().start()
    else:
        if InternetChecker():
            InternetChecker().stop()
            del type(InternetChecker)._instances[InternetChecker]
        elif not RemoteSyncWorker():
            RemoteSyncWorker().initialize()
            RemoteSyncWorker().start()


class BackgroundHandler(metaclass=Singleton):

    def set_intervention_cb(self, cb):
        Intervention().set_callback(cb)

    def set_notification_cb(self, cb):
        Notification().set_callback(cb)

    def start(self):
        # Avoid blocking the UI thread, Remote Sync initialization can request user intervention.
        threading.Thread(target=self._start).start()

    def _start(self):
        OperationWorker().start()
        check_connection()
        LocalSyncWorker().start()

    def sync_now(self):
        check_connection()
        RemoteSyncWorker().sync_now()

    def stop(self):
        if RemoteSyncWorker():
            RemoteSyncWorker().stop()
        OperationWorker().stop()
        LocalSyncWorker().stop()

        del type(OperationWorker)._instances[OperationWorker]
        del type(RemoteSyncWorker)._instances[RemoteSyncWorker]
        del type(LocalSyncWorker)._instances[LocalSyncWorker]
