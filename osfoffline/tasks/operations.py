import os
import abc
import asyncio
import logging

from osfoffline.database import session
from osfoffline.database import models
from osfoffline.database.utils import save
from osfoffline.tasks.notifications import Notification

logger = logging.getLogger(__name__)


class BaseOperation(abc.ABC):

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError


class LocalKeepFile(BaseOperation):

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def run(self):
        logger.info("Local Keep File: {}".format(self.local))


# Download File
class LocalCreateFile(BaseOperation):
    """Download an individual file from the OSF"""

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Create Local File: {}".format(self.remote))
        db_parent = session.query(models.File).filter(models.File.id == self.remote.parent.id).one()
        path = os.path.join(db_parent.path, self.remote.name)
        with open(path, 'wb') as fobj:
            resp = yield from self.remote.request_session.request('GET', self.remote.raw['links']['download'])
            while True:
                chunk = yield from resp.content.read(1024 * 64)
                if not chunk:
                    break
                fobj.write(chunk)
        yield from resp.release()

        Notification().info("Downloaded File: {}".format(self.remote.name))


class LocalCreateFolder(BaseOperation):
    """Create a folder, and populate the contents of that folder (all files to be downloaded)"""

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Create Local Folder: {}".format(self.remote))
        # db_parent = self.db_from_remote(remote.parent)
        # new_folder = File()
        # os.mkdir(new_folder.path)
        # save(session, new_folder)


# Download File
class LocalUpdateFile(BaseOperation):

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Update Local File: {}".format(self.remote))


class LocalDeleteFile(BaseOperation):

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def run(self):
        logger.info("Delete Local File: {}".format(self.local))


class LocalDeleteFolder(BaseOperation):

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def run(self):
        logger.info("Delete Local Folder: {}".format(self.local))


# Upload File
class RemoteCreateFile(BaseOperation):

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def run(self):
        logger.info("Create Remote File: {}".format(self.local))


class RemoteCreateFolder(BaseOperation):

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def run(self):
        logger.info("Create Remote Folder: {}".format(self.local))


# Upload File
class RemoteUpdateFile(BaseOperation):

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def run(self):
        logger.info("Update Remote File: {}".format(self.local))


class RemoteDeleteFile(BaseOperation):

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Delete Remote File: {}".format(self.remote))


class RemoteDeleteFolder(BaseOperation):

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Delete Remote Folder: {}".format(self.remote))


class DatabaseFileCreate(BaseOperation):

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Database File Create: {}".format(self.remote))


class DatabaseFolderCreate(BaseOperation):

    def __init__(self, node, remote):
        self.node = node
        self.remote = remote

    @asyncio.coroutine
    def run(self):
        logger.info("Database Folder Create: {}".format(self.remote))
        save(session, models.File(
            id=self.remote.id,
            name=self.remote.name,
            type=self.remote.kind,
            provider=self.remote.provider,
            osf_path=self.remote.id,
            user=session.query(models.User).one(),
            parent=(self.remote.parent and self.remote.parent.id) or None,
            node=self.node
        ))


class DatabaseFileDelete(BaseOperation):

    def __init__(self, db):
        self.db = db

    @asyncio.coroutine
    def run(self):
        logger.info("Database File Delete: {}".format(self.db))


class DatabaseFolderDelete(BaseOperation):

    def __init__(self, db):
        self.db = db

    @asyncio.coroutine
    def run(self):
        logger.info("Database Folder Delete: {}".format(self.db))
