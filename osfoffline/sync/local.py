import logging
from pathlib import Path
import threading

from watchdog.observers import Observer

from osfoffline import utils
from osfoffline.utils.authentication import get_current_user
from osfoffline.exceptions import NodeNotFound
from osfoffline.sync.ext.watchdog import ConsolidatedEventHandler
from osfoffline.tasks import operations
from osfoffline.tasks.operations import OperationContext
from osfoffline.utils import Singleton
from osfoffline.tasks.queue import OperationWorker


logger = logging.getLogger(__name__)


class LocalSyncWorker(ConsolidatedEventHandler, metaclass=Singleton):

    def __init__(self):
        super().__init__()
        self.folder = get_current_user().folder

        self.observer = Observer()
        self.ignore = threading.Event()
        self.observer.schedule(self, self.folder, recursive=True)

    def start(self):
        logger.debug('Starting watchdog observer')
        self.observer.start()

    def stop(self):
        logger.debug('Stopping LocalSyncWorker')
        # observer is actually a separate child thread and must be join()ed
        self.observer.stop()
        self.join()

    def join(self):
        self.observer.join()
        logger.debug('LocalSyncWorker Stopped')

    def dispatch(self, event):
        if self.ignore.is_set():
            return logger.debug('Ignoring event {}'.format(event))
        super().dispatch(event)

    def on_moved(self, event):
        logger.info('Move event for {}: from {} to {}'.format('directory' if event.is_directory else 'file',
                                                              event.src_path,
                                                              event.dest_path))
        # Note: OperationContext should extrapolate all attributes from what it is given
        if event.is_directory:
            try:
                # TODO: avoid a lazy context load in this case to catch the NodeNotFound exception?
                _ = OperationContext(local=Path(event.src_path), is_folder=True).remote
                return self.put_event(operations.RemoteMoveFolder(
                    OperationContext(local=Path(event.src_path), is_folder=True),
                    OperationContext(local=Path(event.dest_path), is_folder=True),
                ))
            except NodeNotFound:
                return self.put_event(operations.RemoteCreateFolder(
                    OperationContext(local=Path(event.dest_path), is_folder=True),
                ))

        try:
            # TODO: avoid a lazy context load in this case to catch the NodeNotFound exception?
            _ = OperationContext(local=Path(event.src_path)).remote  # noqa
            return self.put_event(operations.RemoteMoveFile(
                OperationContext(local=Path(event.src_path)),
                OperationContext(local=Path(event.dest_path)),
            ))
        except NodeNotFound:
            return self.put_event(operations.RemoteCreateFile(
                OperationContext(local=Path(event.dest_path)),
            ))

    def on_created(self, event):
        logger.info('Creation event for {}: {}'.format('directory' if event.is_directory else 'file',
                                                       event.src_path))
        node = utils.extract_node(event.src_path)
        path = Path(event.src_path)

        # If the file exists in the database, this is a modification
        # This logic may not be the most correct, #TODO re-evaluate
        if utils.local_to_db(path, node):
            return self.on_modified(event)

        context = OperationContext(local=path, node=node)

        if event.is_directory:
            return self.put_event(operations.RemoteCreateFolder(context))
        return self.put_event(operations.RemoteCreateFile(context))

    def on_deleted(self, event, *args, is_folder=False, **kwargs):
        logger.info('Deletion event for {}: {}'.format('directory' if event.is_directory else 'file',
                                                       event.src_path))
        # A hack: override checking if the passed path is a directory. Since Windows
        # emits folder deletion events as file deletes we need to ignore whether or not
        # a delete event is for a folder. Since the RemoteDelete operation works identically
        # for files and folders we can get away with this here.
        context = OperationContext(local=Path(event.src_path), check_is_folder=False)

        return self.put_event(operations.RemoteDelete(context))

    def on_modified(self, event):
        logger.info('Modification event  for {}: {}'.format('directory' if event.is_directory else 'file',
                                                            event.src_path))
        node = utils.extract_node(event.src_path)
        path = Path(event.src_path)

        # If the file does not exist in the database, this is a create
        # This logic may not be the most correct, #TODO re-evaluate
        if not utils.local_to_db(path, node):
            return self.on_created(event)

        context = OperationContext(local=Path(event.src_path))

        if event.is_directory:
            # FIXME: This branch should never be reached, due to a check in dispatch method
            logger.error("Received unexpected modification event for folder: {}".format(event.src_path))
            return self.put_event(operations.RemoteCreateFolder(context))
        return self.put_event(operations.RemoteUpdateFile(context))

    def put_event(self, event):
        OperationWorker().put(event)
