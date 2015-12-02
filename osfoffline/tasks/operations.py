import abc
import asyncio
import collections
import logging
import os

from osfoffline.database_manager import models
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save


logger = logging.getLogger(__name__)


## TODO: Move into alert handling framework
# Alert data definitions
TaskFailure = collections.namedtuple('TaskFailure', ['event_type', 'exc_msg'])


class BaseOperation(abc.ABC):
    @abc.abstractmethod
    def _run(self):
        """Internal implementation of run method; must be overridden in subclasses"""
        raise NotImplementedError

    def __init__(self,  *args, done_callback=None, **kwargs):
        """
        :param function done_callback: An optional function to be called to store the task result.
        """
        self._done_callback = done_callback

    @asyncio.coroutine
    def run(self):
        """Wrap internal run method with error handling"""
        try:
            self._run()
        except Exception as e:
            result_tuple = self._format_error(e)
            logging.exception('Failed to perform operation {}: {}'.format(err_desc.event_type, err_desc.exc_msg))
        else:
            # TODO: Add a tuple describing the event if it ran successfully
            result_tuple = None

        if self._done_callback is not None:
                self._done_callback(result_tuple)

    def _format_error(self, exc):
        """
        Format the error as a task failure object, which will include sufficient detail to display client-facing errors

        :param Exception exc: The exception raised by task failure
        :return: TaskFailure
        """
        event_type = self.__class__.__name__
        return TaskFailure(event_type, str(exc))


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
        print("LocalKeep File: {}".format(self.local))


# Download File
class LocalCreateFile(BaseOperation):
    """Download an individual file from the OSF"""
    def __init__(self, remote, *args, **kwargs):
        """
        :param StorageObject remote: A reference to the remote storage client object
        """
        super(LocalCreateFile, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        logging.info("Create Local File: {}".format(self.remote))
        db_parent = session.query(models.File).filter(models.File.osf_id == self.remote.parent.id).one()
        path = os.path.join(db_parent.path, self.remote.name)
        with open(path, 'wb') as fobj:
            resp = yield from self.remote.request_session.request('GET', self.remote.raw['links']['download'])
            while True:
                chunk = yield from resp.content.read(1024 * 64)
                if not chunk:
                    break
                fobj.write(chunk)
        yield from resp.release()


class LocalCreateFolder(BaseOperation):
    """Create a folder, and populate the contents of that folder (all files to be downloaded)"""
    def __init__(self, remote, *args, **kwargs):
        super(LocalCreateFolder, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        print("Create Local Folder: {}".format(self.remote))
        # db_parent = self.db_from_remote(remote.parent)
        # new_folder = File()
        # os.mkdir(new_folder.path)
        # save(session, new_folder)


# Download File
class LocalUpdateFile(BaseOperation):
    """Download a file from the remote server and modify the database to show task completed"""
    def __init__(self, remote, *args, **kwargs):
        super(LocalUpdateFile, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        print("Update Local File: {}".format(self.remote))


class LocalDeleteFile(BaseOperation):

    def __init__(self, local, *args, **kwargs):
        super(LocalDeleteFile, self).__init__(*args, **kwargs)
        self.local = local

    @asyncio.coroutine
    def _run(self):
        print("Delete Local File: {}".format(self.local))


class LocalDeleteFolder(BaseOperation):
    """Delete a folder (and all containing files) locally"""
    def __init__(self, local, *args, **kwargs):
        super(LocalDeleteFolder, self).__init__(*args, **kwargs)
        self.local = local

    @asyncio.coroutine
    def _run(self):
        print("Delete Local Folder: {}".format(self.local))


class RemoteCreateFile(BaseOperation):
    """Upload a file to the OSF, and update the database to reflect the new OSF id"""
    def __init__(self, local, *args, **kwargs):
        super(RemoteCreateFile, self).__init__(*args, **kwargs)
        self.local = local

    @asyncio.coroutine
    def _run(self):
        print("Create Remote File: {}".format(self.local))


class RemoteCreateFolder(BaseOperation):
    """Upload a folder (and contents) to the OSF and create multiple DB instances to track changes"""
    def __init__(self, local, *args, **kwargs):
        super(RemoteCreateFolder, self).__init__(*args, **kwargs)
        self.local = local

    @asyncio.coroutine
    def _run(self):
        print("Create Remote Folder: {}".format(self.local))


class RemoteUpdateFile(BaseOperation):
    """Upload (already-tracked) file to the OSF (uploads new version)"""
    def __init__(self, local, *args, **kwargs):
        super(RemoteUpdateFile, self).__init__(*args, **kwargs)
        self.local = local

    @asyncio.coroutine
    def _run(self):
        print("Update Remote File: {}".format(self.local))


class RemoteDeleteFile(BaseOperation):
    """Delete a file that already exists remotely"""
    def __init__(self, remote, *args, **kwargs):
        super(RemoteDeleteFile, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        print("Delete Remote File: {}".format(self.remote))


class RemoteDeleteFolder(BaseOperation):
    """Delete a file from the OSF and uopdate the database"""
    def __init__(self, remote, *args, **kwargs):
        super(RemoteDeleteFolder, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        print("Delete Remote Folder: {}".format(self.remote))


class DatabaseFileCreate(BaseOperation):

    def __init__(self, remote, *args, **kwargs):
        super(DatabaseFileCreate, self).__init__(*args, **kwargs)
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        print("Database File Create: {}".format(self.remote))


class DatabaseFolderCreate(BaseOperation):

    def __init__(self, node, remote, *args, **kwargs):
        super(DatabaseFolderCreate, self).__init__(*args, **kwargs)
        self.node = node
        self.remote = remote

    @asyncio.coroutine
    def _run(self):
        print("Database Folder Create: {}".format(self.remote))
        save(session, models.File(
            name=self.remote.name,
            type=self.remote.kind,
            osf_id=self.remote.id,
            provider=self.remote.provider,
            osf_path=self.remote.id,
            user=session.query(models.User).one(),
            parent=(self.remote.parent and self.remote.parent.id) or None,
            node=self.node
        ))


class DatabaseFileDelete(BaseOperation):

    def __init__(self, db, *args, **kwargs):
        super(DatabaseFileDelete, self).__init__(*args, **kwargs)
        self.db = db

    @asyncio.coroutine
    def _run(self):
        print("Database File Delete: {}".format(self.db))


class DatabaseFolderDelete(BaseOperation):

    def __init__(self, db, *args, **kwargs):
        super(DatabaseFolderDelete, self).__init__(*args, **kwargs)
        self.db = db

    @asyncio.coroutine
    def _run(self):
        print("Database Folder Delete: {}".format(self.db))


# class CreateFolder(BaseEvent):
#
#     def __init__(self, path):
#         self.path = path
#
#     @asyncio.coroutine
#     def run(self):
#         # create local node folder on filesystem
#         try:
#             folder_to_create = ProperPath(self.path, is_dir=True)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid target path for folder.')
#             return
#         if not os.path.exists(folder_to_create.full_path):
#             AlertHandler.info(folder_to_create.name, AlertHandler.DOWNLOAD)
#             try:
#                 os.makedirs(folder_to_create.full_path)
#             except Exception:
#                 # TODO: Narrow down this exception and do client side warnings
#                 logging.exception('Exception caught: Problem making a directory.')
#                 return
#
#
# class CreateFile(BaseEvent):
#
#     def __init__(self, path, download_url, osf_query):
#         self.path = path
#         self.osf_query = osf_query
#         self.download_url = download_url
#
#     @asyncio.coroutine
#     def run(self):
#         try:
#             new_file_path = ProperPath(self.path, is_dir=False)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid target path for new file.')
#             return
#         AlertHandler.info(new_file_path.name, AlertHandler.DOWNLOAD)
#         yield from _download_file(new_file_path, self.download_url, self.osf_query)
#
#
# class RenameFolder(BaseEvent):
#
#     def __init__(self, old_path, new_path):
#         self.old_path = old_path
#         self.new_path = new_path
#
#     @asyncio.coroutine
#     def run(self):
#         try:
#             old_folder_path = ProperPath(self.old_path, is_dir=True)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid origin path for renamed folder.')
#             return
#         try:
#             new_folder_path = ProperPath(self.new_path, is_dir=True)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid target path for renamed folder.')
#             return
#
#         AlertHandler.info(new_folder_path.name, AlertHandler.MODIFYING)
#         yield from _rename(old_folder_path, new_folder_path)
#
#
# class RenameFile(BaseEvent):
#
#     def __init__(self, old_path, new_path):
#         self.old_path = old_path
#         self.new_path = new_path
#
#     @asyncio.coroutine
#     def run(self):
#         try:
#             old_file_path = ProperPath(self.old_path, is_dir=False)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid origin path for renamed file.')
#             return
#         try:
#             new_file_path = ProperPath(self.new_path, is_dir=False)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid target path for renamed folder.')
#             return
#
#         AlertHandler.info(new_file_path.name, AlertHandler.MODIFYING)
#         yield from _rename(old_file_path, new_file_path)
#
#
# class UpdateFile(BaseEvent):
#
#     def __init__(self, path, download_url, osf_query):
#         self.path = path
#         self.osf_query = osf_query
#         self.download_url = download_url
#
#     @asyncio.coroutine
#     def run(self):
#         if not isinstance(self.osf_query, OSFQuery):
#             logging.error('Update file query is not an instance of OSFQuery')
#             return
#         if not isinstance(self.download_url, str):
#             logging.error('Update file download_url is not a str.')
#             return
#         try:
#             updated_file_path = ProperPath(self.path, is_dir=False)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid target path for updated file.')
#             return
#         AlertHandler.info(updated_file_path.name, AlertHandler.MODIFYING)
#         yield from _download_file(updated_file_path, self.download_url, self.osf_query)
#
#
# class DeleteFolder(BaseEvent):
#
#     def __init__(self, path):
#         self.path = path
#
#     @asyncio.coroutine
#     def run(self):
#         try:
#             folder_to_delete = ProperPath(self.path, is_dir=True)
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Invalid source path for deleted folder.')
#             return
#
#         AlertHandler.info(folder_to_delete.name, AlertHandler.DELETING)
#         try:
#             shutil.rmtree(
#                 folder_to_delete.full_path,
#                 onerror=lambda a, b, c: logging.warning('local node not deleted because it does not exist.')
#             )
#         except Exception:
#             # TODO: Narrow down this exception and do client side warnings
#             logging.exception('Exception caught: Problem removing the tree.')
#             return
#
#
# class DeleteFile(BaseEvent):
#
#     def __init__(self, path):
#         self.path = path
#
#     @asyncio.coroutine
#     def run(self):
#         file_to_delete = ProperPath(self.path, is_dir=False)
#         AlertHandler.info(file_to_delete.name, AlertHandler.DELETING)
#         try:
#             os.remove(file_to_delete.full_path)
#         except FileNotFoundError:
#             logging.warning(
#                 'file not deleted because does not exist on local filesystem. inside delete_local_file_folder (2)')
#
#
# @asyncio.coroutine
# def _download_file(path, url, osf_query):
#     if not isinstance(path, ProperPath):
#         logging.error("New file path is not a ProperPath.")
#         return
#     if not isinstance(url, str):
#         logging.error("New file URL is not a string.")
#         return
#     try:
#         resp = yield from osf_query.make_request(url)
#     except (aiohttp.errors.ClientOSError):
#         AlertHandler.warn("Please install operating system updates")
#         logging.exception("SSL certificate error")
#         return
#     except (aiohttp.errors.ClientConnectionError, aiohttp.errors.ClientTimeoutError):
#         # FIXME: Consolidate redundant messages
#         AlertHandler.warn("Bad Internet Connection")
#         logging.exception("Bad Internet Connection")
#         return
#     except (aiohttp.errors.HttpMethodNotAllowed, aiohttp.errors.BadHttpMessage):
#         AlertHandler.warn("Do not have access to file.")
#         logging.exception("Do not have access to file.")
#         return
#     except aiohttp.errors.HttpBadRequest:
#         AlertHandler.warn("Problem accessing file.")
#         logging.exception("Exception caught downloading file.")
#         return
#     except Exception:
#         logging.exception("Exception caught: problem downloading file.")
#         return
#     try:
#         with open(path.full_path, 'wb') as fd:
#             while True:
#                 chunk = yield from resp.content.read(2048)
#                 if not chunk:
#                     break
#                 fd.write(chunk)
#         resp.close()
#     except OSError:
#         AlertHandler.warn("unable to open file")
#
#
# @asyncio.coroutine
# def _rename(old_path, new_path):
#     if not isinstance(old_path, ProperPath):
#         logging.error("Old path for rename is not a ProperPath.")
#     if not isinstance(new_path, ProperPath):
#         logging.error("Old path for rename is not a ProperPath.")
#     try:
#         AlertHandler.info(new_path.name, AlertHandler.MODIFYING)
#         os.renames(old_path.full_path, new_path.full_path)
#     except FileNotFoundError:
#         logging.warning('renaming of file/folder failed because file/folder not there')
