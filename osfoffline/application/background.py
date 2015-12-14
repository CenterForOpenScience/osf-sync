import logging
import threading

from osfoffline import settings
from osfoffline.database import models
from osfoffline.database import session
from osfoffline.sync.local import LocalSyncWorker
from osfoffline.sync.remote import RemoteSyncWorker
from osfoffline.tasks import Intervention, Notification
from osfoffline.tasks.queue import OperationWorker
from osfoffline.utils import Singleton


logger = logging.getLogger(__name__)


class BackgroundWorker(metaclass=Singleton):

    # TODO: Find a good fix for ulimit setting
    # try:
    #     self.observer.start()  # start
    # except OSError as e:
    #     # FIXME: Document these limits and provide better user notification.
    #     #    See http://pythonhosted.org/watchdog/installation.html for limits.
    #     raise RuntimeError('Limit of watched items reached') from e

    def set_intervention_cb(self, cb):
        Intervention().set_callback(cb)

    def set_notification_cb(self, cb):
        Notification().set_callback(cb)

    def start(self):
        OperationWorker().start()

        RemoteSyncWorker().initialize()

        RemoteSyncWorker().start()
        LocalSyncWorker().start()

        # logger.debug('Starting Remote Sync')
        # try:
        #     self.remote_sync.start()
        # except Exception as e:
        #     logger.exception(e)
        # logging.debug('Background event loop exited')

    def sync_now(self):
        RemoteSyncWorker().sync_now()

    def stop(self):
        OperationWorker().stop()
        RemoteSyncWorker().stop()
        LocalSyncWorker().stop()

        OperationWorker().join()
        RemoteSyncWorker().join()
        LocalSyncWorker().join()
