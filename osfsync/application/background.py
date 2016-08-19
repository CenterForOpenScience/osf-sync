import logging
import threading

from osfsync.sync.local import LocalSyncWorker
from osfsync.sync.remote import RemoteSyncWorker
from osfsync.tasks import Intervention, Notification
from osfsync.tasks.queue import OperationWorker
from osfsync.utils import Singleton
from osfsync.utils.internetchecker import check_internet
from osfsync.utils.internetchecker import require_internet

logger = logging.getLogger(__name__)


class BackgroundHandler(metaclass=Singleton):

    def __init__(self):
        self._sync_now_thread = None

    def set_intervention_cb(self, cb):
        Intervention().set_callback(cb)

    def set_notification_cb(self, cb):
        Notification().set_callback(cb)

    def start(self):
        # Avoid blocking the UI thread, Remote Sync initialization can request user intervention.
        # Daemon threads do not prevent the application from exitting
        threading.Thread(target=self._start, daemon=True).start()

    def sync_now(self):
        # Only call sync now if the previous sync now has exitted
        if self._sync_now_thread and self._sync_now_thread.is_alive():
            logger.debug('Ignore sync_now another sync_now is starting')
            return
        # Daemon threads do not prevent the application from exitting
        # Avoid blocking the UI thread, will block if the internet is down
        self._sync_now_thread = threading.Thread(target=self._sync_now, daemon=True).start()

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
            self.start()
        else:
            RemoteSyncWorker().sync_now()

    def stop(self):
        # Attempting to stop a stopped or never started thread deadlocks
        if RemoteSyncWorker().is_alive():
            RemoteSyncWorker().stop()
        if OperationWorker().is_alive():
            OperationWorker().stop()
        if LocalSyncWorker().is_alive():
            LocalSyncWorker().stop()

        del type(OperationWorker)._instances[OperationWorker]
        del type(RemoteSyncWorker)._instances[RemoteSyncWorker]
        del type(LocalSyncWorker)._instances[LocalSyncWorker]

    def refresh(self):
        logger.debug('Refreshing workers')
        if LocalSyncWorker().is_alive():
            LocalSyncWorker()._watch_folder()
