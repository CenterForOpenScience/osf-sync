import os
import asyncio
import logging
import hashlib
import itertools

from osfoffline import settings
from osfoffline.client.osf import OSFClient
from osfoffline.exceptions.item_exceptions import InvalidItemType, FolderNotInFileSystem
from osfoffline.sync.audit import FolderAuditor


logger = logging.getLogger(__name__)


class RemoteSync:

    COMPONENTS_FOLDER_NAME = 'Components'

    def __init__(self, operation_queue, intervention_queue, user):
        self.operation_queue = operation_queue
        self.intervention_queue = intervention_queue
        self.user = user
        self.client = OSFClient(self.user.oauth_token)

        self._sync_now_fut = asyncio.Future()

        if not os.path.isdir(self.user.osf_local_folder_path):
            raise FolderNotInFileSystem

    @asyncio.coroutine
    def initialize(self):
        logger.info('Beginning initial sync')
        yield from self._check(True)
        logger.info('Initial sync finished')

    @asyncio.coroutine
    def _check(self, initial):
        nodes = [
            node for node in
            self.user.top_level_nodes
            if node.osf_id in self.user.guid_for_top_level_nodes_to_sync
        ]
        for node in nodes:
            logger.info('Resyncing node {}'.format(node))
            remote = yield from self.client.get_node(node.osf_id)
            yield from FolderAuditor(node, self.operation_queue, self.intervention_queue, remote, initial=initial).crawl()

        logger.info('Finishing intervention queue')
        yield from self.intervention_queue.join()
        logger.info('Finishing operation queue')
        yield from self.operation_queue.join()

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
            yield from self._check(False)
            logger.info('Finished remote sync')
