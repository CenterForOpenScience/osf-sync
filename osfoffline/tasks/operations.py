import abc
import asyncio
import logging
import os
import json
import shutil

from pathlib import Path

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


class OperationContext:

    @classmethod
    def create(cls, local=None, db=None, remote=None, node=None, is_folder=False):
        if not node and db:
            node = db.node
        if not node and local:
            node = utils.extract_node(str(local))
        if not node and remote:
            pass  # TODO run extract node

        if not local and db:
            local = Path(db.path)

        if local and not db:
            db = utils.local_to_db(local, node, is_folder=is_folder)
        if remote and not db:
            db = session.query(models.File).filter(models.File.id == remote.id).one()

        if not remote and db:
            remote = utils.db_to_remote(db)
        return cls(local=local, db=db, remote=remote, node=node)

    def __init__(self, local=None, db=None, remote=None, node=None):
        if not node and db:
            node = db.node
        if not node and local:
            node = utils.extract_node(str(local))
        if not node and remote:
            pass  # TODO run extract node

        self.db = db
        self.node = node
        self.local = local
        self.remote = remote

    def __repr__(self):
        return '<{}({}, {}, {}, {})>'.format(self.__class__.__name__, self.node, self.local, self.db, self.remote)


class BaseOperation(abc.ABC):

    @abc.abstractmethod
    def _run(self):
        """Internal implementation of run method; must be overridden in subclasses"""
        raise NotImplementedError

    @asyncio.coroutine
    def run(self, dry=False):
        """Wrap internal run method"""
        logger.info('{!r}'.format(self))
        if not dry:
            return (yield from self._run())

    def __init__(self, context):
        self._context = context

    @property
    def db(self):
        return self._context.db

    @property
    def local(self):
        return self._context.local

    @property
    def remote(self):
        return self._context.remote

    @property
    def node(self):
        return self._context.node

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self._context)


class MoveOperation(BaseOperation):

    def __init__(self, context, dest_context):
        self._context = context
        self._dest_context = dest_context


class LocalKeepFile(BaseOperation):
    """
    Keep the local copy of the file by making a backup, and ensure that the new (copy of) the file
        will not be uploaded to the OSF
    """

    @asyncio.coroutine
    def _run(self):
        logger.info("Local Keep File: {}".format(self.local))


# Download File
class LocalCreateFile(BaseOperation):
    """Download an individual file from the OSF into a folder that already exists"""

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
        yield from DatabaseCreateFile(OperationContext(remote=self.remote, node=self.node)).run()

        Notification().info('Downloaded File: {}'.format(self.remote.name))


class LocalCreateFolder(BaseOperation):
    """Create a folder, and populate the contents of that folder (all files to be downloaded)"""

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalCreateFolder: {}'.format(self.remote))
        db_parent = session.query(models.File).filter(models.File.id == self.remote.parent.id).one()
        # TODO folder and file with same name
        os.mkdir(os.path.join(db_parent.path, self.remote.name))
        yield from DatabaseCreateFolder(OperationContext(remote=self.remote, node=self.node)).run()
        Notification().info('Downloaded Folder: {}'.format(self.remote.name))


# Download File
class LocalUpdateFile(BaseOperation):
    """Download a file from the remote server and modify the database to show task completed"""

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

        yield from DatabaseUpdateFile(OperationContext(db=db_file, remote=self.remote, node=db_file.node)).run()
        Notification().info('Updated File: {}'.format(self.remote.name))


class LocalDeleteFile(BaseOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalDeleteFile: {}'.format(self.local))

        self.local.unlink()
        yield from DatabaseDeleteFile(OperationContext(db=utils.local_to_db(self.local, self.node))).run()


class LocalDeleteFolder(BaseOperation):
    """Delete a folder (and all containing files) locally"""

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalDeleteFolder: {}'.format(self.local))
        shutil.rmtree(str(self.local))
        yield from DatabaseDeleteFolder(self._context).run()


class RemoteCreateFile(BaseOperation):
    """Upload a file to the OSF, and update the database to reflect the new OSF id"""

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteCreateFile: {}'.format(self.local))
        parent = utils.local_to_db(self.local.parent, self.node)

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, parent.provider, parent.osf_path)
        with self.local.open(mode='rb') as fobj:
            resp = yield from OSFClient().request('PUT', url, data=fobj, params={'name': self.local.name})
        data = yield from resp.json()
        yield from resp.release()
        assert resp.status == 201, '{}\n{}\n{}'.format(resp, url, data)

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = parent

        yield from DatabaseCreateFile(OperationContext(remote=remote, node=self.node)).run()
        Notification().info('Create Remote File: {}'.format(self.local))


class RemoteCreateFolder(BaseOperation):
    """Upload a folder (and contents) to the OSF and create multiple DB instances to track changes"""

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

        yield from DatabaseCreateFolder(OperationContext(remote=remote, node=self.node)).run()
        Notification().info('Create Remote Folder: {}'.format(self.local))


class RemoteUpdateFile(BaseOperation):
    """Upload (already-tracked) file to the OSF (uploads new version)"""

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
        yield from DatabaseUpdateFile(OperationContext(remote=remote,  db=db,  node=self.node)).run()
        Notification().info('Update Remote File: {}'.format(self.local))


class RemoteDeleteFile(BaseOperation):
    """Delete a file that is already known to exist remotely"""

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteDeleteFile: {}'.format(self.remote))
        resp = yield from osf_client.OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        yield from resp.release()
        assert resp.status == 204, resp
        yield from DatabaseDeleteFile(OperationContext(db=session.query(models.File).filter(models.File.id == self.remote.id).one())).run()
        Notification().info('Remote delete file: {}'.format(self.remote))


class RemoteDeleteFolder(BaseOperation):
    """Delete a file from the OSF and update the database"""

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteDeleteFolder: {}'.format(self.remote))
        resp = yield from OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        yield from resp.release()
        assert resp.status == 204, resp
        yield from DatabaseDeleteFolder(OperationContext(db=session.query(models.File).filter(models.File.id == self.remote.id).one())).run()
        Notification().info('Remote delete older: {}'.format(self.remote))


class DatabaseCreateFile(BaseOperation):
    """Create a file in the database, based on information provided from the remote server,
        and attach the file to the specified node"""

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


class DatabaseUpdateFolder(BaseOperation):

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

        save(session, self.db)


class DatabaseDeleteFile(BaseOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseDeleteFile: {}'.format(self.db))
        session.delete(self.db)
        session.commit()


class DatabaseDeleteFolder(BaseOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('DatabaseDeleteFolder: {}'.format(self.db))
        session.delete(self.db)
        session.commit()


class RemoteMoveFolder(MoveOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteMoveFolder: {}'.format(self._context))
        dest_parent = OperationContext.create(local=self._dest_context.local.parent)
        # HACK, TODO Fix me
        dest_parent.remote = yield from dest_parent.remote
        resp = yield from OSFClient().request('POST', self.remote.raw['links']['move'], data=json.dumps({
            'action': 'move',
            'path': dest_parent.db.osf_path if dest_parent.db.parent else '/',
            'rename': self._dest_context.local.name,
        }))
        data =yield from resp.json()
        yield from resp.release()
        assert resp.status in (201, 200), resp

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = session.query(models.File).filter(models.File.id == dest_parent.db.id).one()
        yield from DatabaseUpdateFolder(OperationContext(remote=remote,  db=self.db,  node=self.node)).run()


class RemoteMoveFile(MoveOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('RemoteMoveFile: {}'.format(self._context))
        dest_parent = OperationContext.create(local=self._dest_context.local.parent)
        # HACK, TODO Fix me
        dest_parent.remote = yield from dest_parent.remote
        resp = yield from OSFClient().request('POST', self.remote.raw['links']['move'], data=json.dumps({
            'action': 'move',
            'path': dest_parent.db.osf_path if dest_parent.db.parent else '/',
            'rename': self._dest_context.local.name,
        }))
        data =yield from resp.json()
        yield from resp.release()
        assert resp.status in (201, 200), resp

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = session.query(models.File).filter(models.File.id == dest_parent.db.id).one()
        yield from DatabaseUpdateFile(OperationContext(remote=remote,  db=self.db,  node=self.node)).run()


class LocalMoveFile(MoveOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalMoveFile: {} -> {}'.format(self._context.db.path, self._dest_context.local))
        shutil.move(str(self._context.db.path), str(self._dest_context.local))
        # TODO Handle moved files that were also updated
        yield from DatabaseUpdateFolder(OperationContext(
            db=self._context.db,
            remote=self._dest_context.remote
        )).run()


class LocalMoveFolder(MoveOperation):

    @asyncio.coroutine
    def _run(self):
        logger.info('LocalMoveFolder: {} -> {}'.format(self._context.db.path, self._dest_context.local))
        shutil.move(str(self._context.db.path), str(self._dest_context.local))
        # Note/TODO Cross Node moves will need to have node= specified to the DESTINATION Node below
        yield from DatabaseUpdateFolder(OperationContext(
            db=self._context.db,
            remote=self._dest_context.remote
        )).run()
