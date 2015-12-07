import abc
import asyncio
import logging
import os
import shutil

from osfoffline.client import osf as osf_client
from osfoffline.client.osf import OSFClient
from osfoffline import settings
from osfoffline.database import session
from osfoffline.database import models
from osfoffline.database.utils import save
from osfoffline import utils
from osfoffline.tasks.notifications import Notification
from osfoffline.utils.authentication import get_current_user


logger = logging.getLogger(__name__)


class BaseOperation(abc.ABC):
    @abc.abstractmethod
    def _run(self):
        """Internal implementation of run method; must be overridden in subclasses"""
        raise NotImplementedError

    @asyncio.coroutine
    def run(self):
        """Wrap internal run method"""
        return (yield from self._run())


class LocalKeepFile(BaseOperation):
    """
    Keep the local copy of the file by making a backup, and ensure that the new (copy of) the file
        will not be uploaded to the OSF
    """

    def __init__(self, local):
        self.local = local

    @asyncio.coroutine
    def _run(self):
        logger.info("Local Keep File: {}".format(self.local))


# Download File
class LocalCreateFile(BaseOperation):
    """Download an individual file from the OSF into a folder that already exists"""

    def __init__(self, remote, node):
        """
        :param StorageObject remote: The response from the server describing a remote file
        :param Node node: Database object describing the parent node of the file
        """
        self.node = node
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalCreateFile: {}'.format(self.remote))
        db_parent = session.query(models.File).filter(models.File.id == self.remote.parent.id).one()
        path = os.path.join(db_parent.path, self.remote.name)
        # TODO: Create temp file in target directory while downloading, and rename when done. (check that no temp file exists)
        resp = yield from OSFClient().request('GET', self.remote.raw['links']['download'])
        with open(path, 'wb') as fobj:
            while True:
                chunk = yield from resp.content.read(1024 * 64)
                if not chunk:
                    break
                fobj.write(chunk)
        yield from resp.release()

        # After file is saved, create a new database object to track the file
        #   If the task fails, the database task will be kicked off separately by the auditor on a future cycle
        # TODO: How do we handle a filename being aliased in local storage (due to OS limitations)?
        #   TODO: To keep tasks decoupled, perhaps a shared rename function used by DB task?
        yield from DatabaseCreateFile(self.remote, self.node).run()

        Notification().info('Downloaded File: {}'.format(self.remote.name))


class LocalCreateFolder(BaseOperation):
    """Create a folder, and populate the contents of that folder (all files to be downloaded)"""

    def __init__(self, remote, node):
        self.node = node
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalCreateFolder: {}'.format(self.remote))
        db_parent = session.query(models.File).filter(models.File.id == self.remote.parent.id).one()
        # TODO folder and file with same name
        os.mkdir(os.path.join(db_parent.path, self.remote.name))
        yield from DatabaseCreateFolder(self.remote, self.node).run()
        Notification().info('Downloaded Folder: {}'.format(self.remote.name))


# Download File
class LocalUpdateFile(BaseOperation):
    """Download a file from the remote server and modify the database to show task completed"""

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalUpdateFile: {}'.format(self.remote))
        db_file = session.query(models.File).filter(models.File.id == self.remote.id).one()

        tmp_path = os.path.join(db_file.parent.path, '.~tmp.{}'.format(db_file.name))

        resp = yield from OSFClient().request('GET', self.remote.raw['links']['download'])
        with open(tmp_path, 'wb') as fobj:
            while True:
                chunk = yield from resp.content.read(1024 * 64)
                if not chunk:
                    break
                fobj.write(chunk)
        yield from resp.release()
        shutil.move(tmp_path, db_file.path)

        yield from DatabaseUpdateFile(db_file, self.remote, db_file.node).run()
        Notification().info('Updated File: {}'.format(self.remote.name))


class LocalDeleteFile(BaseOperation):

    def __init__(self, local, node):
        self.local = local
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalDeleteFile: {}'.format(self.local))
        os.remove(self.local.full_path)
        yield from DatabaseDeleteFile(utils.local_to_db(self.local, self.node)).run()


class LocalDeleteFolder(BaseOperation):
    """Delete a folder (and all containing files) locally"""

    def __init__(self, local, node):
        self.local = local
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalDeleteFolder: {}'.format(self.local))
        shutil.rmtree(self.local.full_path)
        yield from DatabaseDeleteFile(utils.local_to_db(self.local, self.node)).run()


class RemoteCreateFile(BaseOperation):
    """Upload a file to the OSF, and update the database to reflect the new OSF id"""

    def __init__(self, local, node):
        self.local = local
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteCreateFile: {}'.format(self.local))
        parent = utils.local_to_db(self.local.parent, self.node)

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, parent.provider, parent.osf_path)
        with open(self.local.full_path, 'rb') as fobj:
            resp = yield from OSFClient().request('PUT', url, data=fobj, params={'name': self.local.name})
        data = yield from resp.json()
        yield from resp.release()
        assert resp.status == 201, '{}\n{}\n{}'.format(resp, url, data)

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = parent

        yield from DatabaseCreateFile(remote, self.node).run()
        Notification().info('Create Remote File: {}'.format(self.local))


class RemoteCreateFolder(BaseOperation):
    """Upload a folder (and contents) to the OSF and create multiple DB instances to track changes"""

    def __init__(self, local, node):
        self.node = node
        self.local = local

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteCreateFolder: {}'.format(self.local))
        parent = utils.local_to_db(self.local.parent, self.node)

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, parent.provider, parent.osf_path)
        resp = yield from OSFClient().request('PUT', url, params={'kind': 'folder', 'name': self.local.name})
        data = yield from resp.json()
        yield from resp.release()
        assert resp.status == 201, '{}\n{}\n{}'.format(resp, url, data)

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>/
        remote.id = remote.id.replace(remote.provider + '/', '').rstrip('/')
        remote.parent = parent

        yield from DatabaseCreateFolder(remote, self.node).run()
        Notification().info('Create Remote Folder: {}'.format(self.local))


class RemoteUpdateFile(BaseOperation):
    """Upload (already-tracked) file to the OSF (uploads new version)"""

    def __init__(self, local, node):
        self.node = node
        self.local = local

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteUpdateFile: {}'.format(self.local))
        db = utils.local_to_db(self.local, self.node)

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, db.provider, db.osf_path)
        with open(self.local.full_path, 'rb') as fobj:
            resp = yield from OSFClient().request('PUT', url, data=fobj, params={'name': self.local.name})
        data = yield from resp.json()
        yield from resp.release()
        assert resp.status == 200, '{}\n{}\n{}'.format(resp, url, data)
        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = db.parent
        # TODO: APIv2 will give back endpoint that can be parsed. Waterbutler may return something *similar* and need to coerce to work with task object
        yield from DatabaseUpdateFile(db, remote, self.node).run()
        Notification().info('Update Remote File: {}'.format(self.local))


class RemoteDeleteFile(BaseOperation):
    """Delete a file that is already known to exist remotely"""

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteDeleteFile: {}'.format(self.remote))
        resp = yield from osf_client.OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        yield from resp.release()
        assert resp.status == 204, resp
        yield from DatabaseDeleteFile(session.query(models.File).filter(models.File.id == self.remote.id).one()).run()
        Notification().info('Remote delete file: {}'.format(self.remote))


class RemoteDeleteFolder(BaseOperation):
    """Delete a file from the OSF and update the database"""

    def __init__(self, remote):
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteDeleteFolder: {}'.format(self.remote))
        resp = yield from OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        yield from resp.release()
        assert resp.status == 204, resp
        yield from DatabaseDeleteFolder(session.query(models.File).filter(models.File.id == self.remote.id).one()).run()
        Notification().info('Remote delete older: {}'.format(self.remote))


class RemoteMoveFile(BaseOperation):

    def __init__(self, src, dest, node):
        self.src = src
        self.dest = dest
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info('Move Remote File: {}'.format(self.local))


class DatabaseCreateFile(BaseOperation):
    """Create a file in the database, based on information provided from the remote server,
        and attach the file to the specified node"""

    def __init__(self, remote, node):
        """
        :param StorageObject remote: The response from the server describing a remote file
        :param Node node: Database object describing the parent node of the file
        """
        self.node = node
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseCreateFile: {}'.format(self.remote))

        parent = self.remote.parent.id if self.remote.parent else None

        save(session, models.File(
            id=self.remote.id,
            name=self.remote.name,
            kind=self.remote.kind,
            provider=self.remote.provider,
            user=get_current_user(),
            parent_id=parent,
            node_id=self.node.id,
            size=self.remote.size,
            md5=self.remote.extra['hashes']['md5'],
            sha256=self.remote.extra['hashes']['sha256'],
        ))


class DatabaseCreateFolder(BaseOperation):

    def __init__(self, remote, node):
        self.remote = remote
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseCreateFolder: {}'.format(self.remote))

        parent = self.remote.parent.id if self.remote.parent else None

        save(session, models.File(
            id=self.remote.id,
            name=self.remote.name,
            kind=self.remote.kind,
            provider=self.remote.provider,
            user=get_current_user(),
            parent_id=parent,
            node_id=self.node.id
        ))


class DatabaseUpdateFile(BaseOperation):

    def __init__(self, db, remote, node):
        self.db = db
        self.node = node
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseUpdateFile: {}'.format(self.db))

        parent = self.remote.parent.id if self.remote.parent else None

        self.db.name = self.remote.name
        self.db.kind = self.remote.kind
        self.db.provider = self.remote.provider
        self.db.user = get_current_user()
        self.db.parent_id = parent
        self.db.node_id = self.node.id
        self.db.size = self.remote.size
        self.db.md5 = self.remote.extra['hashes']['md5']
        self.db.sha256 = self.remote.extra['hashes']['sha256']

        save(session, self.db)


class DatabaseDeleteFile(BaseOperation):

    def __init__(self, db):
        self.db = db

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseDeleteFile: {}'.format(self.db))
        session.delete(self.db)


class DatabaseDeleteFolder(BaseOperation):

    def __init__(self, db):
        self.db = db

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseDeleteFolder: {}'.format(self.db))
        session.delete(self.db)
