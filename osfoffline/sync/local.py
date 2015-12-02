import asyncio
import logging

from watchdog.observers import Observer

from osfoffline.tasks import operations
from osfoffline.sync.ext.watchdog import ConsolidatedEventHandler


logger = logging.getLogger(__name__)


class LocalSync(ConsolidatedEventHandler):

    def __init__(self, user, operation_queue, intervention_queue):
        super().__init__()
        self.folder = user.osf_local_folder_path

        self.observer = Observer()
        self.operation_queue = operation_queue
        self.intervention_queue = intervention_queue
        self.observer.schedule(self, self.folder, recursive=True)

    def start(self):
        logger.info('Starting watchdog observer')
        self.observer.start()

    def stop(self):
        logger.debug('Stopping observer thread')
        # observer is actually a separate child thread and must be join()ed
        self.observer.stop()
        self.observer.join()

    def on_moved(self, event):
        logger.info('Moved {}: from {} to {}'.format((event.is_directory and 'directory') or 'file', event.src_path, event.dest_path))

    def on_created(self, event):
        logger.info('Created {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))

    def on_deleted(self, event):
        logger.info('Deleted {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))

    def on_modified(self, event):
        logger.info('Modified {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))

    def put_event(self, event):
        self.operation_queue._loop.call_soon_threadsafe(asyncio.ensure_future, self.operation_queue.put(event))
