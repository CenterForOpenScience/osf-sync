# -*- coding: utf-8 -*-
import os
import asyncio
import logging
import hashlib
import itertools

# from watchdog.events import (
#     DirDeletedEvent,
#     FileDeletedEvent,
#     FileModifiedEvent,
#     FileCreatedEvent,
#     DirCreatedEvent,
# )
# from watchdog.observers import Observer
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from osfoffline.database_manager.db import session
from osfoffline.polling_osf_manager.osf_query import OSFQuery
from osfoffline.database_manager.models import User, Node, File, Base
from osfoffline.exceptions.item_exceptions import InvalidItemType, FolderNotInFileSystem
from osfoffline.exceptions.local_db_sync_exceptions import LocalDBBothNone, IncorrectLocalDBMatch
from osfoffline.utils.path import ProperPath
from osfoffline.polling_osf_manager.api_url_builder import api_url_for, NODES, USERS
from osfoffline import settings

from osfoffline.client.osf import OSFClient


logger = logging.getLogger(__name__)


class DatabaseSync:

    COMPONENTS_FOLDER_NAME = 'Components'

    def __init__(self, queue, user):
        self.queue = queue
        self.user = user
        self.client = OSFClient(self.user.oauth_token)
        # self.osf_query = OSFQuery(asyncio.get_event_loop(), self.user.oauth_token)
        self.osf_folder = self.user.osf_local_folder_path

        if not os.path.isdir(self.osf_folder):
            raise FolderNotInFileSystem

        self.osf_path = ProperPath(self.osf_folder, True)

    @asyncio.coroutine
    def check(self):
        logger.info('Beginning initial sync')
        events, nodes = [], [
            node for node in
            self.user.top_level_nodes
            if node.osf_id in self.user.guid_for_top_level_nodes_to_sync
        ]
        for node in nodes:
            logger.info('Resyncing node {}'.format(node))
            node = yield from self.client.get_node(node.osf_id)
            yield from Auditor(node, self.queue).audit()
        logger.info('Initial sync finished')

    def _match_local_remote(self, local_list, remote_list):
        ret = {}
        for local in local_list:
            ret.setdefault((local.name, local.is_dir), [None, None])[0] = local

        for remote in remote_list:
            ret.setdefault((remote.name, remote.is_dir), [None, None])[1] = remote

        return ret

    @asyncio.coroutine
    def _crawl_node(self, node, local_path='/', remote_path='/'):
        logger.debug('Crawling node {} at path {}'.format(node, local_path))
        events, directories = [], []
        resources = self._match_local_remote(
            self._list_local_dir(node, local_path),
            (yield from self._list_remote_dir(node, remote_path))
        )

        for (name, is_dir), (local, remote) in resources.items():
            if is_dir:
                directories.append((
                    getattr(local, 'fullpath', None),
                    getattr(remote, 'osf_id', None)
                ))
            event = yield from self._infer_event(local, remote)
            if event is not None:
                events.append(event)
                # DO SOMETHING HERE
                # yield from self.queue.put(event)

        # yield from self.queue.join()

        for local_dir, remote_dir in directories:
            yield from self._crawl_node(node, local_dir, remote_dir)

        return events

    @asyncio.coroutine
    def _list_remote_dir(self, node, remote_folder):
        if remote_folder is None:
            return []

        if remote_folder != '/':
            return (yield from remote_folder.get_children())

        return (yield from (yield from self.client.get_node(node.osf_id)).get_storage('osfstorage'))

    def _list_local_dir(self, node, path):
        if path is None:
            return []
        path = os.path.join(node.path, settings.OSF_STORAGE_FOLDER, path.lstrip('/'))
        try:
            return [
                ProperPath(
                    os.path.join(path, name),
                    os.path.isdir(os.path.join(path, name))
                )
                for name in os.listdir(path)
                if name not in settings.IGNORED_NAMES
            ]
        except FileNotFoundError:
            return []

    @asyncio.coroutine
    def _infer_event(self, local_file, remote_file):
        try:
            if remote_file:
                db_file = session.query(File).filter(File.is_folder == remote_file.is_dir, File.osf_id == remote_file.id).one()
            elif local_file:
                db_file = next(
                    f for f in
                    session.query(File).filter(File.is_folder == local_file.is_dir, File.name == local_file.name)
                    if f.path == local_file.full_path
                )
            else:
                return None
        except (NoResultFound, StopIteration) as e:
            logger.debug(e)
            if local_file and remote_file:
                local_sha256 = self._get_sha256(local_file.full_path)
                if remote_file.extra['hashes']['sha256'] == local_sha256:
                    return print('insert remote in local database, local file is current remote file')
                if local_sha256 in [version.extra['hashes']['sha256'] for version in (yield from remote_file.get_versions())]:
                    return print('download latest file, current local file is old version')
                raise ValueError('Found conflicting files remotely and locally that are not tracked, ask user')
            elif local_file and not remote_file:
                # Upload to OSF
                if local_file.is_dir:
                    return print('send to user intervention queue: DirCreatedEvent(local_file.full_path)')
                else:
                    return print('FileCreatedEvent(local_file.full_path)')
            elif not local_file and remote_file:
                # Download from OSF
                # Actual poller will handle this case :+1:
                return None
            else:
                raise ValueError('EVERYTHING IS NONE HOW DID YOU GET HERE')

        if local_file and remote_file:
            if not local_file.is_dir:
                return None # Directory exits, nothing to do
            if os.path.getsize(local_file.full_path) == db_file.size and db_file.sha256 == self._get_sha256(local_file.full_path):
                return None  # File has not changed
            if remote_file.extra['hashes']['sha256'] == db_file.sha256:
                # File has been changed locally
                return print('FileModifiedEvent(local_file.full_path)')
            raise ValueError('Upstream file and local file has been modified since last sync')
        elif local_file and not remote_file:
            if local_file.size == db_file.size and db_file.sha256 == self._get_sha256(local_file):
                return None  # Poller will delete this file
            # Upstream has been deleted but the local file has been modified.
            # Go ahead and upload. User can delete it if they'd like
            # TODO might have to remove the database entry here
            if local_file.is_dir:
                return print('DirCreatedEvent(local_file.full_path)')
            else:
                return print('FileCreatedEvent(local_file.full_path)')
        elif not local_file and remote_file:
            # Poller will re-download the file. Only persist deletes that happened whilst online
            return None
        else:
            # TODO delete file from DB. Why is there anyways?
            return None

    def _get_sha256(self, path, chunk_size=1024**2):
        s = hashlib.sha256()
        with open(path, 'rb') as fobj:
            while True:
                chunk = fobj.read(chunk_size)
                if not chunk:
                    break
                s.update(chunk)
        return s.hexdigest()
