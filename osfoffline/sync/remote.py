import asyncio
import hashlib
import logging
import os

from pathlib import Path

from osfoffline import settings
from osfoffline.client.osf import OSFClient
from osfoffline.database import session
from osfoffline.database.models import Node, File
from osfoffline.sync.exceptions import FolderNotInFileSystem
from osfoffline.sync.ext.audit import FolderAuditor
from osfoffline.utils.path import ProperPath
from osfoffline.utils.authentication import get_current_user


logger = logging.getLogger(__name__)


class RemoteSync:

    COMPONENTS_FOLDER_NAME = 'Components'

    def __init__(self, user, ignore_watchdog, operation_queue):
        self.ignore_watchdog = ignore_watchdog
        self.operation_queue = operation_queue
        self.user = user

        self._sync_now_fut = asyncio.Future()

        if not os.path.isdir(self.user.folder):
            raise FolderNotInFileSystem

    @asyncio.coroutine
    def initialize(self):
        logger.info('Beginning initial sync')
        yield from self._check(True)
        logger.info('Initial sync finished')

    @asyncio.coroutine
    def _check(self, initial):
        for node in session.query(Node).all():
            logger.info('Resyncing node {}'.format(node))
            remote, local = yield from self._preprocess_node(node)
            auditor = FolderAuditor(node, self.operation_queue, remote, local, initial=initial)
            yield from auditor.audit()

        logger.info('Finishing operation queue')
        yield from self.operation_queue.join()

    @asyncio.coroutine
    def _preprocess_node(self, node):
        remote_node = yield from OSFClient().get_node(node.id)
        remote = yield from remote_node.get_storage(id='osfstorage')
        local = ProperPath(os.path.join(node.path, settings.OSF_STORAGE_FOLDER), True)
        if not os.path.exists(local.full_path):
            session.query(File).filter(File.node_id == node.id).delete()
        os.makedirs(local.full_path, exist_ok=True)
        return remote, local

    @asyncio.coroutine
    def sync_now(self):
        if self._sync_now_fut.done():
            return
        self._sync_now_fut.set_result(None)

    @asyncio.coroutine
    def start(self):
        while True:
            # Note: CHECK_INTERVAL must be < 24 hours
            logger.info('Sleeping for {} seconds'.format(settings.REMOTE_CHECK_INTERVAL))
            try:
                yield from asyncio.wait_for(self._sync_now_fut, timeout=settings.REMOTE_CHECK_INTERVAL)
                logger.info('Sleep interruptted, syncing now')
            except asyncio.TimeoutError:
                pass
            finally:
                self._sync_now_fut = asyncio.Future()

            logger.info('Beginning remote sync')
            self.ignore_watchdog.set()
            yield from self._check(False)
            self.ignore_watchdog.clear()
            logger.info('Finished remote sync')

    @asyncio.coroutine
    def _check(self, initial):
        for node in session.query(Node).all():
            logger.info('Resyncing node {}'.format(node))
            remote, local = yield from self._preprocess_node(node)
            auditor = FolderAuditor(node, self.operation_queue, remote, local, initial=initial)
            yield from auditor.audit()

        logger.info('Finishing operation queue')
        yield from self.operation_queue.join()
