import asyncio
import hashlib
import itertools
import logging
import os

from pathlib import Path

from osfoffline import settings
from osfoffline.client.osf import OSFClient
from osfoffline.database import session
from osfoffline.database.models import Node, File
from osfoffline.sync.exceptions import FolderNotInFileSystem
from osfoffline.sync.ext.auditor import Auditor
from osfoffline.sync.ext.auditor import EventType
from osfoffline.utils.authentication import get_current_user
from osfoffline.tasks.resolution import RESOLUTION_MAP


logger = logging.getLogger(__name__)


class RemoteSync:

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
        for node in session.query(Node).all():
            self._preprocess_node(node)
        session.commit()
        yield from self._check(True)
        logger.info('Initial sync finished')

    def _preprocess_node(self, node):
        local = Path(os.path.join(node.path, settings.OSF_STORAGE_FOLDER))
        if not local.exists():
            logger.warning('Clearing files for node {}'.format(node))
            session.query(File).filter(File.node_id == node.id).delete()
        os.makedirs(str(local), exist_ok=True)

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
    def _check(self, _):
        files = []
        resolutions = []
        local_events, remote_events = yield from Auditor().audit()

        for is_folder in (True, False):
            for conflict in sorted(set(local_events.keys()) & set(remote_events.keys()), key=len):
                if conflict.endswith(os.path.sep) == is_folder:
                    continue
                local, remote = local_events[conflict], remote_events[conflict]
                res = RESOLUTION_MAP[(True, local.event_type, remote.event_type)](local, remote, local_events, remote_events)
                if asyncio.iscoroutine(res):
                    res = yield from res
                if res:
                    if isinstance(res, list):
                        resolutions.extend(res)
                    logger.error('Conflict at {} between {} and {}\nResolved with {}'.format(conflict, local.event_type, remote.event_type, res))
                else:
                    logger.warning('Conflict at {} between {} and {} required no resolution'.format(conflict, local.event_type, remote.event_type))

        # for conflict in set(local_events.keys()) & set(remote_events.keys()):
        #     if conflict.endswith(os.path.sep):
        #         raise Exception()
        #     local, remote = local_events.pop(conflict), remote_events.pop(conflict)
        #     res = RESOLUTION_MAP[(False, local.event_type, remote.event_type)](local, remote, local_events, remote_events)
        #     resolutions.extend(res)
        #     if res:
        #         logger.error('Conflict at {} between {} and {}\nResolved with {}'.format(conflict, local.event_type, remote.event_type, res))
        #     else:
        #         logger.warning('Conflict at {} between {} and {} required no resolution'.format(conflict, local.event_type, remote.event_type))

        td = TreeDict()
        directories = []
        for event in sorted(itertools.chain(local_events.values(), remote_events.values()), key=lambda x: x.src_path.count(os.path.sep)):
        # for event in sorted(itertools.chain(local_events.values(), remote_events.values()), ):
            if event.is_directory:
                if event.event_type == EventType.UPDATE:
                    continue
                if settings.OSF_STORAGE_FOLDER in event.src_path:
                    directories.append(event)
            else:
                td[event.src_path.split(os.path.sep)] = event

        # TODO Maybe not need to check for conflicts?
        for event in sorted(directories, key=lambda x: x.src_path.count(os.path.sep), reverse=True):
            parts = event.src_path.split(os.path.sep)[:-1]
            if event.event_type not in (EventType.MOVE, EventType.DELETE):
                logging.warning('Ignoring event {}'.format(event.src_path))
                continue
            if parts in td and td[parts] == event:
                logging.warning('Ignoring duplicate move event {}'.format(event.src_path))
                continue
            conflicts = [
                child for child in td.children(parts)
                if (event.location, event.event_type) != (child.location, child.event_type)
            ]
            if conflicts:
                logger.error('Detected {} conflicts for folder {}. ({})'.format(len(conflicts), event.src_path, [x.context for x in conflicts]))
            del td[parts]

        for operation in itertools.chain(resolutions, (event.operation() for event in directories), (event.operation() for event in td.children())):
            yield from self.operation_queue.put(operation)

        yield from self.operation_queue.join()


def flatten(dict_obj, acc):
    for value in dict_obj.values():
        if isinstance(value, dict):
            flatten(value, acc)
        else:
            acc.append(value)
    return acc


class TreeDict:

    def __init__(self):
        self._inner = {}

    def __setitem__(self, keys, value):
        inner = self._inner
        for key in keys[:-1]:
            inner = inner.setdefault(key, {})
        inner[keys[-1]] = value

    def __getitem__(self, keys):
        if not isinstance(keys, (tuple, list)):
            keys = (keys,)
        inner = self._inner
        for key in keys:
            inner = inner[key]
        return inner

    def children(self, keys=None):
        try:
            sub_dict = self[keys] if keys is not None else self._inner
        except KeyError:
            return []
        return flatten(sub_dict, [])

    def __contains__(self, keys):
        inner = self._inner
        try:
            self[keys]
        except KeyError:
            return False
        return True

    def __delitem__(self, keys):
        self[keys] = {}
