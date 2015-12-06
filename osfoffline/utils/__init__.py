import os
import asyncio
import threading

from osfoffline import settings
from osfoffline.database import session
from osfoffline.database import models
from osfoffline.utils.authentication import get_current_user


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        key = (getattr(cls, 'thread_safe', False) and cls) or (threading.get_ident(), cls)
        if key not in cls._instances:
            cls._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[key]


def ensure_event_loop():
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
    return session.query(models.Node).filter(models.Node.id == node_id).one()


def local_to_db(local, node):
    db = session.query(models.File).filter(models.File.parent == None, File.node == node).one()
    parts = local.full_path.replace(node.path, '').split('/')
    for part in parts:
        for child in db.children:
            if child.name == part:
                db = child
    if db.path.rstrip('/') != local.full_path.rstrip('/') or db.is_folder != local.is_dir:
        raise Exception()
    return db


def db_to_remote(db):
    # Fix circular import
    from osfoffline.client import osf
    return ensure_event_loop().run_until_complete(
        osf.StorageObject.load(osf.OSFClient().request_session, db.id)
    )
