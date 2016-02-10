import logging
import signal
import threading

from osfoffline.sync.local import LocalSyncWorker
from osfoffline.sync.remote import RemoteSyncWorker
from osfoffline.tasks import Intervention, Notification
from osfoffline.tasks.queue import OperationWorker
from osfoffline.utils import Singleton


logger = logging.getLogger(__name__)


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

        RemoteSyncWorker().initialize()

        RemoteSyncWorker().start()
        LocalSyncWorker().start()

    def sync_now(self):
        RemoteSyncWorker().sync_now()

    def stop(self):
        RemoteSyncWorker().stop()
        OperationWorker().stop()
        LocalSyncWorker().stop()

        del type(OperationWorker)._instances[OperationWorker]
        del type(RemoteSyncWorker)._instances[RemoteSyncWorker]
        del type(LocalSyncWorker)._instances[LocalSyncWorker]
