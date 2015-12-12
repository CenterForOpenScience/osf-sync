import asyncio
import logging

from pathlib import Path
from watchdog.observers import Observer

from osfoffline import utils
from osfoffline.sync.ext.watchdog import ConsolidatedEventHandler
from osfoffline.tasks import operations
from osfoffline.tasks.operations import OperationContext


logger = logging.getLogger(__name__)


class LocalSync(ConsolidatedEventHandler):

    def __init__(self, user, ignore_event, operation_queue):
        super().__init__()
        self.folder = user.folder

        self.observer = Observer()
        self.ignore = ignore_event
        self.operation_queue = operation_queue
        self.observer.schedule(self, self.folder, recursive=True)

    def start(self):
        logger.info('Starting watchdog observer')
        self.observer.start()

    def stop(self):
        logger.debug('Stopping observer thread')
        # observer is actually a separate child thread and must be join()ed
        self.observer.stop()
        self.observer.join()

    def dispatch(self, event):
        if self.ignore.is_set():
            return logger.debug('Ignoring event {}'.format(event))
        super().dispatch(event)

    def on_moved(self, event):
        logger.info('Moved {}: from {} to {}'.format((event.is_directory and 'directory') or 'file', event.src_path, event.dest_path))
        # Note: OperationContext should extrapolate all attributes from what it is given
        if event.is_directory:
            return self.put_event(operations.RemoteMoveFolder(
                OperationContext.create(local=Path(event.src_path), is_folder=True),
                OperationContext.create(local=Path(event.dest_path), is_folder=True),
            ))
        return self.put_event(operations.RemoteMoveFile(
            OperationContext.create(local=Path(event.src_path)),
            OperationContext.create(local=Path(event.dest_path)),
        ))

    def on_created(self, event):
        logger.info('Created {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))
        node = utils.extract_node(event.src_path)
        path = Path(event.src_path)

        # If the file exists in the database, this is a modification
        # This logic may not be the most correct, #TODO re-evaluate
        if utils.local_to_db(path, node):
            return self.on_modified(event)

        context = OperationContext.create(local=path, node=node)

        if event.is_directory:
            return self.put_event(operations.RemoteCreateFolder(context))
        return self.put_event(operations.RemoteCreateFile(context))

    def on_deleted(self, event):
        logger.info('Deleted {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))
        # node = utils.extract_node(event.src_path)
        # local = Path(event.src_path)
        # db = utils.local_to_db(local, node)
        # remote = utils.db_to_remote(db)
        # context = OperationContext(local=local, db=db, remote=remote, node=node)
        context = OperationContext.create(local=Path(event.src_path))

        if event.is_directory:
            return self.put_event(operations.RemoteDeleteFolder(context))
        return self.put_event(operations.RemoteDeleteFile(context))

    def on_modified(self, event):
        logger.info('Modified {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))
        # path = Path(event.src_path)
        # node = utils.extract_node(event.src_path)
        # context = OperationContext(local=path, node=node)
        context = OperationContext.create(local=Path(event.src_path))

        if event.is_directory:
            # WHAT DO
            return self.put_event(operations.RemoteCreateFolder(context))
        return self.put_event(operations.RemoteUpdateFile(context))

    def put_event(self, event):
        self.operation_queue._loop.call_soon_threadsafe(asyncio.ensure_future, self.operation_queue.put(event))
