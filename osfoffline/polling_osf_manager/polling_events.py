import os
import shutil
import asyncio
import logging

import aiohttp

from osfoffline.utils.path import ProperPath
from osfoffline.polling_osf_manager.osf_query import OSFQuery
import osfoffline.alerts as AlertHandler


class PollingEvent(object):
    def __init__(self):
        pass

    @asyncio.coroutine
    def run(self):
        pass


class CreateFolder(PollingEvent):
    def __init__(self, path):
        super().__init__()
        self.path = path

    @asyncio.coroutine
    def run(self):
        # create local node folder on filesystem
        try:
            folder_to_create = ProperPath(self.path, is_dir=True)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid target path for folder.')
            return
        if not os.path.exists(folder_to_create.full_path):
            AlertHandler.info(folder_to_create.name, AlertHandler.DOWNLOAD)
            try:
                os.makedirs(folder_to_create.full_path)
            except Exception:
                # TODO: Narrow down this exception and do client side warnings
                logging.exception('Exception caught: Problem making a directory.')
                return


class CreateFile(PollingEvent):
    def __init__(self, path, download_url, osf_query):
        super().__init__()
        self.path = path
        self.osf_query = osf_query
        self.download_url = download_url

    @asyncio.coroutine
    def run(self):
        try:
            new_file_path = ProperPath(self.path, is_dir=False)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid target path for new file.')
            return
        AlertHandler.info(new_file_path.name, AlertHandler.DOWNLOAD)
        yield from _download_file(new_file_path, self.download_url, self.osf_query)


class RenameFolder(PollingEvent):
    def __init__(self, old_path, new_path):
        super().__init__()

        self.old_path = old_path
        self.new_path = new_path

    @asyncio.coroutine
    def run(self):
        try:
            old_folder_path = ProperPath(self.old_path, is_dir=True)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid origin path for renamed folder.')
            return
        try:
            new_folder_path = ProperPath(self.new_path, is_dir=True)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid target path for renamed folder.')
            return

        AlertHandler.info(new_folder_path.name, AlertHandler.MODIFYING)
        yield from _rename(old_folder_path, new_folder_path)


class RenameFile(PollingEvent):
    def __init__(self, old_path, new_path):
        super().__init__()

        self.old_path = old_path
        self.new_path = new_path

    @asyncio.coroutine
    def run(self):
        try:
            old_file_path = ProperPath(self.old_path, is_dir=False)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid origin path for renamed file.')
            return
        try:
            new_file_path = ProperPath(self.new_path, is_dir=False)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid target path for renamed folder.')
            return

        AlertHandler.info(new_file_path.name, AlertHandler.MODIFYING)
        yield from _rename(old_file_path, new_file_path)


class UpdateFile(PollingEvent):
    def __init__(self, path, download_url, osf_query):
        super().__init__()
        self.path = path
        self.osf_query = osf_query
        self.download_url = download_url

    @asyncio.coroutine
    def run(self):
        if not isinstance(self.osf_query, OSFQuery):
            logging.error('Update file query is not an instance of OSFQuery')
            return
        if not isinstance(self.download_url, str):
            logging.error('Update file download_url is not a str.')
            return
        try:
            updated_file_path = ProperPath(self.path, is_dir=False)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid target path for updated file.')
            return
        AlertHandler.info(updated_file_path.name, AlertHandler.MODIFYING)
        yield from _download_file(updated_file_path, self.download_url, self.osf_query)


class DeleteFolder(PollingEvent):
    def __init__(self, path):
        super().__init__()
        self.path = path

    @asyncio.coroutine
    def run(self):
        try:
            folder_to_delete = ProperPath(self.path, is_dir=True)
        except Exception:
            # TODO: Narrow down this exception and do client side warnings
            logging.exception('Exception caught: Invalid source path for deleted folder.')
            return
        # this works on systems that use file descriptors.
        # thus, linux, mac are supported.
        # todo: is windows supported??
        if shutil.rmtree.avoids_symlink_attacks:
            AlertHandler.info(folder_to_delete.name, AlertHandler.DELETING)
            try:
                shutil.rmtree(
                    folder_to_delete.full_path,
                    onerror=lambda a, b, c: logging.warning('local node not deleted because it does not exist.')
                )
            except Exception:
                # TODO: Narrow down this exception and do client side warnings
                logging.exception('Exception caught: Problem removing the tree.')
                return
        else:
            logging.error("Cannot delete folder without risking symlink attack. Method not implemented.")
            return


class DeleteFile(PollingEvent):
    def __init__(self, path):
        super().__init__()
        self.path = path

    @asyncio.coroutine
    def run(self):
        file_to_delete = ProperPath(self.path, is_dir=False)
        AlertHandler.info(file_to_delete.name, AlertHandler.DELETING)
        try:
            os.remove(file_to_delete.full_path)
        except FileNotFoundError:
            logging.warning(
                'file not deleted because does not exist on local filesystem. inside delete_local_file_folder (2)')


@asyncio.coroutine
def _download_file(path, url, osf_query):
    if not isinstance(path, ProperPath):
        logging.error("New file path is not a ProperPath.")
        return
    if not isinstance(url, str):
        logging.error("New file URL is not a string.")
        return
    try:
        resp = yield from osf_query.make_request(url)
    except (aiohttp.errors.ClientOSError):
        AlertHandler.warn("Invalid permissions for OSF folder")
        logging.exception("Invalid permissions for OSF folder")
    except (aiohttp.errors.ClientConnectionError, aiohttp.errors.ClientTimeoutError):
        # FIXME: Consolidate redundant messages
        AlertHandler.warn("Bad Internet Connection")
        logging.exception("Bad Internet Connection")
        return
    except (aiohttp.errors.HttpMethodNotAllowed, aiohttp.errors.BadHttpMessage):
        AlertHandler.warn("Do not have access to file.")
        logging.exception("Do not have access to file.")
        return
    except aiohttp.errors.HttpBadRequest:
        AlertHandler.warn("Problem accessing file.")
        logging.exception("Exception caught downloading file.")
        return
    except Exception:
        logging.exception("Exception caught: problem downloading file.")
        return
    try:
        with open(path.full_path, 'wb') as fd:
            while True:
                chunk = yield from resp.content.read(2048)
                if not chunk:
                    break
                fd.write(chunk)
        resp.close()
    except OSError:
        AlertHandler.warn("unable to open file")


@asyncio.coroutine
def _rename(old_path, new_path):
    if not isinstance(old_path, ProperPath):
        logging.error("Old path for rename is not a ProperPath.")
    if not isinstance(new_path, ProperPath):
        logging.error("Old path for rename is not a ProperPath.")
    try:
        AlertHandler.info(new_path.name, AlertHandler.MODIFYING)
        os.renames(old_path.full_path, new_path.full_path)
    except FileNotFoundError:
        logging.warning('renaming of file/folder failed because file/folder not there')
