# -*- coding: utf-8 -*-
import asyncio
import logging
import threading

from watchdog.observers import Observer

from osfoffline.database import models
from osfoffline.database import session
from osfoffline.sync.local import LocalSync
from osfoffline.sync.remote import RemoteSync
from osfoffline.tasks.queue import OperationsQueue, InterventionQueue


logger = logging.getLogger(__name__)


class BackgroundWorker(threading.Thread):

    def __init__(self):
        super().__init__()

        # Start out with null variables for NoneType errors rather than Attribute Errors
        self.user = None
        self.root_folder = None

        self.loop = None
        self.poller = None
        self.observer = None

    def _ensure_event_loop(self):
        """Ensure the existance of an eventloop
        Useful for contexts where get_event_loop() may raise an exception.
        Such as multithreaded applications

        :returns: The new event loop
        :rtype: BaseEventLoop
        """
        try:
            return asyncio.get_event_loop()
        except (AssertionError, RuntimeError):
            asyncio.set_event_loop(asyncio.new_event_loop())

        # Note: No clever tricks are used here to dry up code
        # This avoids an infinite loop if settings the event loop ever fails
        return asyncio.get_event_loop()

    def run(self):
        logger.debug('Background worker starting')
        self.loop = self.ensure_event_loop()
        # self.loop.set_debug(True)

        self.user = session.query(models.User).one()
        self.root_folder = self.user.osf_local_folder_path

        self.operation_queue = OperationsQueue()
        self.operation_queue_task = asyncio.ensure_future(self.operation_queue.start())
        self.operation_queue_task.add_done_callback(self._handle_exception)

        self.intervention_queue = InterventionQueue()

        logger.debug('Initializing Remote Sync')
        self.remote_sync = RemoteSync(self.operation_queue, self.intervention_queue, user)
        self.loop.run_until_complete(self.remote_sync.initialize())

        logger.debug('Starting Local Sync')
        self.local_sync = LocalSync(user, self.operation_queue, self.intervention_queue)
        self.local_sync.start()

        logger.debug('Starting Remote Sync')
        self.remote_sync_task = asyncio.ensure_future(self.remote_sync.start())
        self.remote_sync_task.add_done_callback(self._handle_exception)

        logging.debug('Starting background event loop')
        try:
            self.loop.run_forever()
        except Exception as e:
            logger.exception(e)
        finally:
            self.stop()
        logging.debug('Background event loop exited')

    # def start_folder_observer(self):
    #     # if something inside the folder changes, log it to config dir
    #     # create event handler
    #     self.event_handler = osf_event_handler.OSFEventHandler(
    #         self.root_folder,
    #         loop=self.loop
    #     )
    #
    #     # todo: if config actually has legitimate data. use it.
    #
    #     # start
    #     self.observer = Observer()  # create observer. watched for events on files.
    #     # attach event handler to observed events. make observer recursive
    #     self.observer.schedule(self.event_handler, self.root_folder, recursive=True)
    #
    #     # TODO: Fix reindexing functionality to not delete everything when a sync fails or exits unsafely
    #     # LocalDBSync(self.user.osf_local_folder_path, self.observer, self.user).emit_new_events()
    #
    #     try:
    #         self.observer.start()  # start
    #     except OSError as e:
    #         # FIXME: Document these limits and provide better user notification.
    #         #    See http://pythonhosted.org/watchdog/installation.html for limits.
    #         raise RuntimeError('Limit of watched items reached') from e

    def stop(self):
        # Note: This method is **NOT called from this current thread**
        # All method/function/routines/etc MUST be thread safe from here out
        if not self.poller or not self.observer:
            raise RuntimeError('OSF poller or folder observer is not defined, Background work was not correctly initialized')

        logger.debug('Stopping background worker')

        logger.debug('Stopping OSF polling')
        self.loop.call_soon_threadsafe(self.remote_sync.stop)

        logger.debug('Stopping local sync thread')
        self.local_sync.stop()

        logger.debug('Stopping the event loop')
        # Note: this is what actually stops the current thread
        # Calls self.join, be careful with what is on the event loop
        self.stop_loop(close=True)

    def stop_loop(self, close=False):
        """ WARNING: Only pass in 'close' if you plan on creating a new loop afterwards
        """
        if not self.loop:
            logger.warning('loop never initialized')
            return

        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            logging.debug('Stopped event loop')
            self.join()

        if close:
            self.loop.close()
            logging.debug('Closed event loop')
