import abc
import logging
import os
import json
import shutil

from pathlib import Path

from osfoffline import settings
from osfoffline import utils
from osfoffline.client import osf as osf_client
from osfoffline.client.osf import OSFClient
from osfoffline.database import models
from osfoffline.database import Session
from osfoffline.database.utils import save
from osfoffline.tasks.notifications import Notification
from osfoffline.utils.authentication import get_current_user


logger = logging.getLogger(__name__)


class OperationContext:

    @property
    def node(self):
        if self._node:
            return self._node

        if self._db:
            self._node = self._db.node
        elif self._local:
            self._node = utils.extract_node(str(self._local))
        elif self._remote:
            pass  # TODO run extract node

        return self._node

    @property
    def db(self):
        if self._db:
            return self._db
        if self._local:
            self._db = utils.local_to_db(self._local, self.node, is_folder=self._is_folder)
        elif self._remote:
            self._db = Session().query(models.File).filter(models.File.id == self._remote.id).one()
        return self._db

    @property
    def remote(self):
        if self._remote:
            return self._remote
        if self._db or self._local:
            self._remote = utils.db_to_remote(self.db)
        return self._remote

    @property
    def local(self):
        if self._local:
            return self._local
        if self._db:
            self._local = Path(self._db.path)
        return self._local

    def __init__(self, local=None, db=None, remote=None, node=None, is_folder=False):
        self._db = db
        self._node = node
        self._local = local
        self._remote = remote
        self._is_folder = is_folder

    def __repr__(self):
        return '<{}({}, {}, {}, {})>'.format(self.__class__.__name__, self._node, self._local, self._db, self._remote)


class BaseOperation(abc.ABC):

    @abc.abstractmethod
    def _run(self):
        """Internal implementation of run method; must be overridden in subclasses"""
        raise NotImplementedError

    def run(self, dry=False):
        """Wrap internal run method"""
        logger.debug('Running {!r}'.format(self))
        if not dry:
            return self._run()

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


# Download File
class LocalCreateFile(BaseOperation):
    """Download an individual file from the OSF into a folder that already exists"""

    def _run(self):
        db_parent = Session().query(models.File).filter(models.File.id == self.remote.parent.id).one()
        path = os.path.join(db_parent.path, self.remote.name)
        # TODO: Create temp file in target directory while downloading, and rename when done. (check that no temp file exists)
        resp = OSFClient().request('GET', self.remote.raw['links']['download'], stream=True)
        with open(path, 'wb') as fobj:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    fobj.write(chunk)

        # After file is saved, create a new database object to track the file
        #   If the task fails, the database task will be kicked off separately by the auditor on a future cycle
        # TODO: How do we handle a filename being aliased in local storage (due to OS limitations)?
        #   TODO: To keep tasks decoupled, perhaps a shared rename function used by DB task?
        DatabaseCreateFile(OperationContext(remote=self.remote, node=self.node)).run()

        Notification().info('Downloaded File: {}'.format(self.remote.name))


class LocalCreateFolder(BaseOperation):
    """Create a folder, and populate the contents of that folder (all files to be downloaded)"""

    def _run(self):
        db_parent = Session().query(models.File).filter(models.File.id == self.remote.parent.id).one()
        # TODO folder and file with same name
        os.mkdir(os.path.join(db_parent.path, self.remote.name))
        DatabaseCreateFolder(OperationContext(remote=self.remote, node=self.node)).run()
        Notification().info('Downloaded Folder: {}'.format(self.remote.name))


# Download File
class LocalUpdateFile(BaseOperation):
    """Download a file from the remote server and modify the database to show task completed"""

    def _run(self):
        db_file = Session().query(models.File).filter(models.File.id == self.remote.id).one()

        tmp_path = os.path.join(db_file.parent.path, '.~tmp.{}'.format(db_file.name))

        resp = OSFClient().request('GET', self.remote.raw['links']['download'], stream=True)
        with open(tmp_path, 'wb') as fobj:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    fobj.write(chunk)
        shutil.move(tmp_path, db_file.path)

        DatabaseUpdateFile(OperationContext(db=db_file, remote=self.remote, node=db_file.node)).run()
        Notification().info('Updated File: {}'.format(self.remote.name))


class LocalDeleteFile(BaseOperation):

    def _run(self):
        self.local.unlink()
        DatabaseDeleteFile(OperationContext(db=utils.local_to_db(self.local, self.node))).run()


class LocalDeleteFolder(BaseOperation):
    """Delete a folder (and all containing files) locally"""

    def _run(self):
        shutil.rmtree(str(self.local))
        DatabaseDeleteFolder(self._context).run()


class RemoteCreateFile(BaseOperation):
    """Upload a file to the OSF, and update the database to reflect the new OSF id"""

    def _run(self):
        parent = utils.local_to_db(self.local.parent, self.node)

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, parent.provider, parent.osf_path)
        with self.local.open(mode='rb') as fobj:
            resp = OSFClient().request('PUT', url, data=fobj, params={'name': self.local.name})
        data = resp.json()
        assert resp.status_code == 201, '{}\n{}\n{}'.format(resp, url, data)

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = parent

        DatabaseCreateFile(OperationContext(remote=remote, node=self.node)).run()
        Notification().info('Create Remote File: {}'.format(self.local))


class RemoteCreateFolder(BaseOperation):
    """Upload a folder (and contents) to the OSF and create multiple DB instances to track changes"""

    def _run(self):
        parent = utils.local_to_db(self.local.parent, self.node)

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, parent.provider, parent.osf_path)
        resp = OSFClient().request('PUT', url, params={'kind': 'folder', 'name': self.local.name})
        data = resp.json()
        assert resp.status_code == 201, '{}\n{}\n{}'.format(resp, url, data)

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>/
        remote.id = remote.id.replace(remote.provider + '/', '').rstrip('/')
        remote.parent = parent

        DatabaseCreateFolder(OperationContext(remote=remote, node=self.node)).run()
        Notification().info('Create Remote Folder: {}'.format(self.local))


class RemoteUpdateFile(BaseOperation):
    """Upload (already-tracked) file to the OSF (uploads new version)"""

    def _run(self):
        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, self.db.provider, self.db.osf_path)
        with open(str(self.local), 'rb') as fobj:
            resp = OSFClient().request('PUT', url, data=fobj, params={'name': self.local.name})
        data = resp.json()
        assert resp.status_code == 200, '{}\n{}\n{}'.format(resp, url, data)
        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = self.db.parent
        DatabaseUpdateFile(OperationContext(remote=remote, db=self.db, node=self.node)).run()
        Notification().info('Update Remote File: {}'.format(self.local))


class RemoteDeleteFile(BaseOperation):
    """Delete a file that is already known to exist remotely"""

    def _run(self):
        resp = osf_client.OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        assert resp.status_code == 204, resp
        DatabaseDeleteFile(OperationContext(db=Session().query(models.File).filter(models.File.id == self.remote.id).one())).run()
        Notification().info('Remote delete file: {}'.format(self.remote))


class RemoteDeleteFolder(BaseOperation):
    """Delete a file from the OSF and update the database"""

    def _run(self):
        resp = OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        assert resp.status_code == 204, resp
        DatabaseDeleteFolder(OperationContext(db=Session().query(models.File).filter(models.File.id == self.remote.id).one())).run()
        Notification().info('Remote delete older: {}'.format(self.remote))


class DatabaseCreateFile(BaseOperation):
    """Create a file in the database, based on information provided from the remote server,
        and attach the file to the specified node"""

    def _run(self):
        parent = self.remote.parent.id if self.remote.parent else None

        save(Session(), models.File(
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

    def _run(self):
        parent = self.remote.parent.id if self.remote.parent else None

        save(Session(), models.File(
            id=self.remote.id,
            name=self.remote.name,
            kind=self.remote.kind,
            provider=self.remote.provider,
            user=get_current_user(),
            parent_id=parent,
            node_id=self.node.id
        ))


class DatabaseUpdateFile(BaseOperation):

    def _run(self):
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

        save(Session(), self.db)


class DatabaseUpdateFolder(BaseOperation):

    def _run(self):
        parent = self.remote.parent.id if self.remote.parent else None

        self.db.name = self.remote.name
        self.db.kind = self.remote.kind
        self.db.provider = self.remote.provider
        self.db.user = get_current_user()
        self.db.parent_id = parent
        self.db.node_id = self.node.id

        save(Session(), self.db)


class DatabaseDeleteFile(BaseOperation):

    def _run(self):
        Session().delete(self.db)
        Session().commit()


class DatabaseDeleteFolder(BaseOperation):

    def _run(self):
        Session().delete(self.db)
        Session().commit()


class RemoteMoveFolder(MoveOperation):

    def _run(self):
        dest_parent = OperationContext(local=self._dest_context.local.parent)
        resp = OSFClient().request('POST', self.remote.raw['links']['move'], data=json.dumps({
            'action': 'move',
            'path': dest_parent.db.osf_path if dest_parent.db.parent else '/',
            'rename': self._dest_context.local.name,
        }))
        data = resp.json()
        assert resp.status_code in (201, 200), resp

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = Session().query(models.File).filter(models.File.id == dest_parent.db.id).one()
        DatabaseUpdateFolder(OperationContext(remote=remote, db=self.db, node=self.node)).run()


class RemoteMoveFile(MoveOperation):

    def _run(self):
        dest_parent = OperationContext(local=self._dest_context.local.parent)

        resp = OSFClient().request('POST', self.remote.raw['links']['move'], data=json.dumps({
            'action': 'move',
            'path': dest_parent.db.osf_path if dest_parent.db.parent else '/',
            'rename': self._dest_context.local.name,
        }))
        data = resp.json()
        assert resp.status_code in (201, 200), resp

        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>
        remote.id = remote.id.replace(remote.provider + '/', '')
        remote.parent = Session().query(models.File).filter(models.File.id == dest_parent.db.id).one()
        DatabaseUpdateFile(OperationContext(remote=remote, db=self.db, node=self.node)).run()


class LocalMoveFile(MoveOperation):

    def _run(self):
        shutil.move(str(self._context.db.path), str(self._dest_context.local))
        # TODO Handle moved files that were also updated
        DatabaseUpdateFolder(OperationContext(
            db=self._context.db,
            remote=self._dest_context.remote
        )).run()


class LocalMoveFolder(MoveOperation):

    def _run(self):
        shutil.move(str(self._context.db.path), str(self._dest_context.local))
        # Note/TODO Cross Node moves will need to have node= specified to the DESTINATION Node below
        DatabaseUpdateFolder(OperationContext(
            db=self._context.db,
            remote=self._dest_context.remote
        )).run()
