import os

from sqlalchemy.orm.exc import NoResultFound

from osfoffline import settings
from osfoffline.database import session
from osfoffline.database import models
from osfoffline.exceptions import NodeNotFound
from osfoffline.utils.authentication import get_current_user


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def extract_node(path):
    """Given a file path extract the node id and return the loaded Database object
    Visual, how this method works:
        '/root/OSF/Node - 1244/Components/Node - 1482/OSF Storage/OSF Storage/OSF Storage/file.txt'
        '/OSF/Node - 1244/Components/Node - 1482/OSF Storage/OSF Storage/OSF Storage/file.txt'
        ['/OSF/Node - 1244/Components/Node - 1482/', '', '', '/file.txt']
        '/OSF/Node - 1244/Components/Node - 1482/'
        ['Node - 1244', 'Components', 'Node - 1482']
        'Node - 1482'
        1482
    """
    node_id = path.replace(get_current_user().folder, '').split(settings.OSF_STORAGE_FOLDER)[0].strip(os.path.sep).split(os.path.sep)[-1].split(' - ')[-1]
    try:
        return session.query(models.Node).filter(models.Node.id == node_id).one()
    except NoResultFound:
        raise NodeNotFound(path)


def local_to_db(local, node, is_folder=False):
    db = session.query(models.File).filter(models.File.parent == None, models.File.node == node).one()
    parts = str(local).replace(node.path, '').split('/')
    for part in parts:
        for child in db.children:
            if child.name == part:
                db = child
    if db.path.rstrip('/') != str(local).rstrip('/') or db.is_folder != (local.is_dir() or is_folder):
        return None
    return db


def db_to_remote(db):
    # Fix circular import
    from osfoffline.client import osf

    if db.parent is None:
        return _remote_root(db)
    return osf.StorageObject.load(osf.OSFClient().request_session, db.id)


def _remote_root(db):
    # Fix circular import
    from osfoffline.client import osf
    return next(
        storage
        for storage in
        osf.NodeStorage.load(osf.OSFClient().request_session, db.node.id)
        if storage.provider == db.provider
    )
