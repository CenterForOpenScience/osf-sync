import abc
import asyncio
import logging
import os
import shutil

import aiohttp

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


class TaskReport:
    """Report on whether a task succeeded or failed. Should include sufficient information for the UI layer to display
        a user-friendly message describing the event that was performed"""
    def __init__(self, event_type, success=True, exc=None):
        """
        :param str event_type: Name of the event type
        :param bool success: Whether the task succeeded or failed
        :param Exception exc: (optional) An exception object can be provided with a traceback
        """
        self.event_type = event_type
        self.success = success
        self.exc = exc


class BaseOperation(abc.ABC):
    @abc.abstractmethod
    def _run(self):
        """Internal implementation of run method; must be overridden in subclasses"""
        raise NotImplementedError

    def __init__(self,  *args, done_callback=None, **kwargs):
        """
        :param function done_callback: An optional function to be called to store the task result.
        """
        # TODO: Evaluate use of done_callback. Main advantage: ability to track status of tasks that fire off secondary tasks.
        self._done_callback = done_callback

    @asyncio.coroutine
    def run(self):
        """Wrap internal run method with error handling"""
        return (yield from self._run())
        # try:
        # except Exception as e:
        #     task_result = self._format_error(e)
        #     logging.exception('Failed to perform operation {}: {}'.format(
        #         task_result.event_type, str(task_result.exc)))
        # else:
        #     # TODO: Add a report describing the event if it ran successfully
        #     task_result = None

        # if self._done_callback is not None:
        #         self._done_callback(task_result)

    def _format_error(self, exc):
        """
        Format the error as a task failure object, which will include sufficient detail to display client-facing errors

        :param Exception exc: The exception raised by task failure
        :return: TaskFailure
        """
        event_type = self.__class__.__name__
        return TaskReport(event_type, success=False, exc=exc)


class LocalKeepFile(BaseOperation):
    """
    Keep the local copy of the file by making a backup, and ensure that the new (copy of) the file
        will not be uploaded to the OSF
    """

    def __init__(self, local, *args, **kwargs):
        super(LocalKeepFile, self).__init__(*args, **kwargs)
        self.local = local

    @asyncio.coroutine
    def _run(self):
        logger.info("Local Keep File: {}".format(self.local))


# Download File
class LocalCreateFile(BaseOperation):
    """Download an individual file from the OSF into a folder that already exists"""
    def __init__(self, remote, node, *args, **kwargs):
        """
        :param StorageObject remote: The response from the server describing a remote file
        :param Node node: Database object describing the parent node of the file
        """
        super(LocalCreateFile, self).__init__(*args, **kwargs)
        self.remote = remote
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Create Local File: {}".format(self.remote))
        Notification().info("Create Local File: {}".format(self.remote))
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

        Notification().info("Downloaded File: {}".format(self.remote.name))


class LocalCreateFolder(BaseOperation):
    """Create a folder, and populate the contents of that folder (all files to be downloaded)"""
    def __init__(self, remote, node, *args, **kwargs):
        super(LocalCreateFolder, self).__init__(*args, **kwargs)
        self.remote = remote
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Create Local Folder: {}".format(self.remote))
        # TODO handle moves better
        session.query(models.File).filter(models.File.id == self.remote.id).delete()
        save(session)
        db_parent = session.query(models.File).filter(models.File.id == self.remote.parent.id).one()
        # TODO folder and file with same name
        os.mkdir(os.path.join(db_parent.path, self.remote.name))
        yield from DatabaseCreateFolder(self.remote, self.node).run()


# Download File
class LocalUpdateFile(BaseOperation):
    """Download a file from the remote server and modify the database to show task completed"""
    def __init__(self, remote, *args, **kwargs):
        super(LocalUpdateFile, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info('Update Local File: {}'.format(self.remote))
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

        Notification().info('Updated File: {}'.format(self.remote.name))


class LocalDeleteFile(BaseOperation):

    def __init__(self, local, node, *args, **kwargs):
        super(LocalDeleteFile, self).__init__(*args, **kwargs)
        self.local = local
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Delete Local File: {}".format(self.local))
        os.remove(self.local.full_path)
        session.delete(utils.local_to_db(self.local, self.node))


class LocalDeleteFolder(BaseOperation):
    """Delete a folder (and all containing files) locally"""
    def __init__(self, local, node, *args, **kwargs):
        super(LocalDeleteFolder, self).__init__(*args, **kwargs)
        self.local = local
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Delete Local Folder: {}".format(self.local))
        os.remove(self.local.full_path)
        session.delete(utils.local_to_db(self.local, self.node))


class RemoteCreateFile(BaseOperation):
    """Upload a file to the OSF, and update the database to reflect the new OSF id"""
    def __init__(self, local, node, *args, **kwargs):
        super(RemoteCreateFile, self).__init__(*args, **kwargs)
        self.local = local
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Create Remote File: {}".format(self.local))
        Notification().info("Create Remote File: {}".format(self.local))
        parent = session.query(models.File).filter(models.File.parent == None, models.File.node == self.node).one()
        parts = self.local.full_path.replace(self.node.path, '').split('/')
        for part in parts:
            for child in parent.children:
                if child.name == part:
                    parent = child

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
        # TODO: APIv2 will give back endpoint that can be parsed. Waterbutler may return something *similar* and need to coerce to work with task object
        yield from DatabaseCreateFile(remote, self.node).run()


class RemoteCreateFolder(BaseOperation):
    """Upload a folder (and contents) to the OSF and create multiple DB instances to track changes"""
    def __init__(self, local, node, *args, **kwargs):
        super(RemoteCreateFolder, self).__init__(*args, **kwargs)
        self.node = node
        self.local = local

    @asyncio.coroutine
    def _run(self):
        logger.info("Create Remote Folder: {}".format(self.local))
        parent = session.query(models.File).filter(models.File.parent == None, models.File.node == self.node).one()
        parts = self.local.full_path.replace(self.node.path, '').split('/')
        for part in parts:
            for child in parent.children:
                if child.name == part:
                    parent = child

        url = '{}/v1/resources/{}/providers/{}/{}'.format(settings.FILE_BASE, self.node.id, parent.provider, parent.osf_path)
        resp = yield from OSFClient().request('PUT', url, params={'kind': 'folder', 'name': self.local.name})
        data = yield from resp.json()
        yield from resp.release()
        assert resp.status == 201, '{}\n{}\n{}'.format(resp, url, data)
        remote = osf_client.File(None, data['data'])
        # WB id are <provider>/<id>/
        remote.id = remote.id.replace(remote.provider + '/', '').rstrip('/')
        remote.parent = parent
        # TODO: APIv2 will give back endpoint that can be parsed. Waterbutler may return something *similar* and need to coerce to work with task object
        yield from DatabaseCreateFolder(remote, self.node).run()


class RemoteUpdateFile(BaseOperation):
    """Upload (already-tracked) file to the OSF (uploads new version)"""
    def __init__(self, local, node, *args, **kwargs):
        super(RemoteUpdateFile, self).__init__(*args, **kwargs)
        self.node = node
        self.local = local

    @asyncio.coroutine
    def _run(self):
        logger.info("Update Remote File: {}".format(self.local))
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
        remote.parent = parent
        # TODO: APIv2 will give back endpoint that can be parsed. Waterbutler may return something *similar* and need to coerce to work with task object
        yield from DatabaseCreateFile(remote, self.node).run()


class RemoteDeleteFile(BaseOperation):
    """Delete a file that is already known to exist remotely"""
    def __init__(self, remote, *args, **kwargs):
        super(RemoteDeleteFile, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info("Delete Remote File: {}".format(self.remote))
        resp = yield from osf_client.OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        yield from resp.release()
        assert resp.status == 204, resp
        yield from DatabaseDeleteFile(session.query(models.File).filter(models.File.id == self.remote.id).one()).run()


class RemoteDeleteFolder(BaseOperation):
    """Delete a file from the OSF and update the database"""
    def __init__(self, remote, *args, **kwargs):
        super(RemoteDeleteFolder, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logger.info("Delete Remote Folder: {}".format(self.remote))
        resp = yield from OSFClient().request('DELETE', self.remote.raw['links']['delete'])
        yield from resp.release()
        assert resp.status == 204, resp
        yield from DatabaseDeleteFolder(session.query(models.File).filter(models.File.id == self.remote.id).one()).run()


class RemoteMoveFile(BaseOperation):
    def __init__(self, src, dest, node):
        self.src = src
        self.dest = dest
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Move Remote File: {}".format(self.local))


class DatabaseCreateFile(BaseOperation):
    """Create a file in the database, based on information provided from the remote server,
        and attach the file to the specified node"""
    # TODO: As written, the dependency on remote object implies it will never create a DB entry unless it is based on data on the server
    #   TODO (local file creation won't trigger DB operation? Is that intentional design?)
    def __init__(self, remote, node, *args, **kwargs):
        """
        :param StorageObject remote: The response from the server describing a remote file
        :param Node node: Database object describing the parent node of the file
        """
        self.node = node
        self.remote = remote
        super(DatabaseCreateFile, self).__init__(*args, **kwargs)

    @asyncio.coroutine
    def _run(self):
        logger.info("Database File Create: {}".format(self.remote))

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

    def __init__(self, remote, node, *args, **kwargs):
        super(DatabaseCreateFolder, self).__init__(*args, **kwargs)
        self.remote = remote
        self.node = node

    @asyncio.coroutine
    def _run(self):
        logger.info("Database Folder Create: {}".format(self.remote))

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


class DatabaseDeleteFile(BaseOperation):

    def __init__(self, db, *args, **kwargs):
        super(DatabaseDeleteFile, self).__init__(*args, **kwargs)
        self.db = db

    @asyncio.coroutine
    def _run(self):
        logger.info("Database File Delete: {}".format(self.db))
        session.delete(self.db)


class DatabaseDeleteFolder(BaseOperation):

    def __init__(self, db, *args, **kwargs):
        super(DatabaseDeleteFolder, self).__init__(*args, **kwargs)
        self.db = db

    @asyncio.coroutine
    def _run(self):
        logger.info("Database Folder Delete: {}".format(self.db))
        session.delete(self.db)
