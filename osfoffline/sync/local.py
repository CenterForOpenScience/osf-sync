import os
import asyncio
import logging

from watchdog.observers import Observer

from osfoffline import settings
from osfoffline.client import osf
from osfoffline.database import session
from osfoffline.database.models import File
from osfoffline.database.models import Node
from osfoffline.sync.ext.watchdog import ConsolidatedEventHandler
from osfoffline.tasks import operations
from osfoffline.utils.authentication import get_current_user
from osfoffline.utils.path import ProperPath


logger = logging.getLogger(__name__)


def extract_node(path):
    """Given a file path extract the node id and return the loaded Database object
    Visual, how this method works:
        '/root/OSF/Node - 1244/Components/Node -1482/OSF Storage/OSF Storage/OSF Storage/file.txt'
        '/OSF/Node - 1244/Components/Node -1482/OSF Storage/OSF Storage/OSF Storage/file.txt'
        ['/OSF/Node - 1244/Components/Node -1482/', '', '', '/file.txt']
        '/OSF/Node - 1244/Components/Node -1482/'
        ['Node - 1244', 'Components', 'Node - 1482']
        'Node - 1482'
        1482
    """
    node_id = path.replace(get_current_user().folder, '').split(settings.OSF_STORAGE_FOLDER)[0].strip(os.path.sep).split(os.path.sep)[-1].split('- ')[-1]
    return session.query(Node).filter(Node.id == node_id).one()


def local_to_db(local, node):
    db = session.query(File).filter(File.parent == None, File.node == node).one()
    parts = local.full_path.replace(node.path, '').split('/')
    for part in parts:
        for child in db.children:
            if child.name == part:
                db = child
    if db.path.rstrip('/') != local.full_path.rstrip('/') or db.is_folder != local.is_dir:
        raise Exception()
    return db


def db_to_remote(db):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        osf.StorageObject.load(osf.OSFClient().request_session, db.id)
    )


class LocalSync(ConsolidatedEventHandler):

    def __init__(self, user, operation_queue):
        super().__init__()
        self.folder = user.folder

        self.observer = Observer()
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

    def on_moved(self, event):
        logger.info('Moved {}: from {} to {}'.format((event.is_directory and 'directory') or 'file', event.src_path, event.dest_path))

    def on_created(self, event):
        logger.info('Created {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))
        node = extract_node(event.src_path)
        path = ProperPath(event.src_path, event.is_directory)
        if event.is_directory:
            return self.put_event(operations.RemoteCreateFolder(path, node))
        return self.put_event(operations.RemoteCreateFile(path, node))

    def on_deleted(self, event):
        logger.info('Deleted {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))
        node = extract_node(event.src_path)
        local = ProperPath(event.src_path, event.is_directory)
        db = local_to_db(local, node)
        remote = db_to_remote(db)

        if event.is_directory:
            return self.put_event(operations.RemoteDeleteFolder(remote, node))
        return self.put_event(operations.RemoteDeleteFile(remote, node))

    def on_modified(self, event):
        logger.info('Modified {}: {}'.format((event.is_directory and 'directory') or 'file', event.src_path))
        node = extract_node(event.src_path)
        path = ProperPath(event.src_path, event.is_directory)
        if event.is_directory:
            # WHAT DO
            return self.put_event(operations.RemoteCreateFolder(path, node))
        return self.put_event(operations.RemoteUpdateFile(path, node))

    def put_event(self, event):
        self.operation_queue._loop.call_soon_threadsafe(asyncio.ensure_future, self.operation_queue.put(event))
