import itertools
import logging
import os
from pathlib import Path
import threading
import time

from sqlalchemy.orm.exc import NoResultFound

from osfoffline import settings

from osfoffline.client.osf import OSFClient, ClientLoadError

from osfoffline.database import Session
from osfoffline.database.models import Node, File
from osfoffline.database.utils import save

from osfoffline.sync.local import LocalSyncWorker
from osfoffline.sync.exceptions import FolderNotInFileSystem
from osfoffline.sync.ext.auditor import (
    Auditor,
    EventType
)

from osfoffline.tasks.notifications import Notification
from osfoffline.tasks.resolution import RESOLUTION_MAP
from osfoffline.tasks.queue import OperationWorker

from osfoffline.utils import Singleton
from osfoffline.utils.authentication import get_current_user


logger = logging.getLogger(__name__)


class RemoteSyncWorker(threading.Thread, metaclass=Singleton):

    def __init__(self):
        super().__init__()
        self.user = get_current_user()
        self.__stop = threading.Event()
        self._sync_now_event = threading.Event()

        if not os.path.isdir(self.user.folder):
            raise FolderNotInFileSystem

    def initialize(self):
        logger.info('Beginning initial sync')
        for node in Session().query(Node).filter(Node.sync).all():
            self._preprocess_node(node)
        Session().commit()
        # TODO No need for this check
        self._check()
        logger.info('Initial sync finished')

    def sync_now(self):
        self._sync_now_event.set()

    def run(self):
        while not self.__stop.is_set():
            # Note: CHECK_INTERVAL must be < 24 hours
            logger.info('Sleeping for {} seconds'.format(settings.REMOTE_CHECK_INTERVAL))
            if self._sync_now_event.wait(timeout=settings.REMOTE_CHECK_INTERVAL):
                if self.__stop.is_set():
                    break
                logger.info('Sleep interrupted, syncing now')
            self._sync_now_event.clear()

            logger.info('Beginning remote sync')
            LocalSyncWorker().ignore.set()

            # Ensure selected node directories exist and db entries created
            for node in Session().query(Node).filter(Node.sync).all():
                try:
                    self._preprocess_node(node, delete=False)
                except OSError:
                    # TODO: If the node folder cannot be created, what further actions must be taken before attempting to sync?
                    # TODO: Should the error be user-facing?
                    logger.exception('Error creating node directory for sync')

            OperationWorker().join_queue()

            try:
                self._check()
            except:
                # TODO: Add user-facing notification?
                msg = 'Error encountered in remote sync operation; will try again later'
                Notification().error(msg)
                logger.exception(msg)

            time.sleep(10)  # FIXME Per icereval, this is "due to watchdog not clearing its event evaluation when the lock is cleared"
            LocalSyncWorker().ignore.clear()
            logger.info('Finished remote sync')
        logger.info('Stopped RemoteSyncWorker')

    def stop(self):
        logger.info('Stopping RemoteSyncWorker')
        self.__stop.set()
        self.sync_now()

    def _orphan_children(self, node, remote_children):
        """It's a hard world out there...
        Delete the database record for any descendant not mirrored remotely.
        Via cascade this will also remove any descedant Nodes and Files.
        The effect of this action is that any files associated with a child Node
        locally for which the remote Node has been deleted are explicitly removed
        from OSFO's auditing and will be ignored.
        """
        children_ids = map(lambda c: c.id, remote_children)
        for record in node.children:
            if record.id not in children_ids:
                Session().delete(record)

    def _preprocess_node(self, node, *, delete=True):
        nodes = [node]
        try:
            remote_node = OSFClient().get_node(node.id)
        except ClientLoadError as err:
            # TODO: maybe special case on status code, but for now treat
            # 40X codes as if the user cannot access the Node any more
            if 400 <= err.status < 500:
                # cascade should automagically delete children
                Session().delete(node)
                return
            else:
                # TODO handle 50X errors
                raise
        stack = remote_node.get_children(lazy=False)
        self._orphan_children(node, stack)
        while len(stack):
            child = stack.pop(0)
            # Ensure the database contains a Node record for each node in the project heirarchy.
            # This must guarentee the remote/database representations of the project heirarchy are
            # fully congruent.
            # TODO: If we want to support syncing only subsets of the project heirarchy then some
            # additional logic could be added here to skip over certain nodes.
            try:
                db_child = Session().query(Node).filter(
                    Node.id == child.id
                ).one()
            except NoResultFound:
                # Setting sync=False notes that the node is implicity synced
                parent = Session().query(Node).filter(
                    Node.id == child.parent.id
                ).one()
                db_child = Node(
                    id=child.id,
                    title=child.title,
                    user=node.user,
                    parent_id=parent.id
                )
                Session().add(db_child)
            nodes.append(db_child)
            children = child.get_children(lazy=False)
            self._orphan_children(db_child, children)
            stack = stack + children
        save(Session())
        for node in nodes:
            local = Path(os.path.join(node.path, settings.OSF_STORAGE_FOLDER))
            if delete and not local.exists():
                logger.warning('Clearing files for node {}'.format(node))
                Session().query(File).filter(File.node_id == node.id).delete()
            os.makedirs(str(local), exist_ok=True)

    def _check(self):
        resolutions = []
        local_events, remote_events = Auditor().audit()

        for is_folder in (True, False):
            for conflict in sorted(set(local_events.keys()) & set(remote_events.keys()), key=lambda x: x.count(os.path.sep)):
                if conflict.endswith(os.path.sep) != is_folder:
                    continue
                try:
                    local, remote = local_events.pop(conflict), remote_events.pop(conflict)
                except KeyError:
                    continue
                res = RESOLUTION_MAP[(is_folder, local.event_type, remote.event_type)](local, remote, local_events, remote_events)
                if res:
                    if isinstance(res, list):
                        resolutions.extend(res)
                    logger.error('Conflict at {} between {} and {}\nResolved with {}'.format(conflict, local.event_type, remote.event_type, res))
                else:
                    logger.warning('Conflict at {} between {} and {} required no resolution'.format(conflict, local.event_type, remote.event_type))

        td = TreeDict()
        directories = []
        for event in sorted(set(itertools.chain(local_events.values(), remote_events.values())), key=lambda x: x.src_path.count(os.path.sep)):
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
                child for child in td.children(keys=parts)
                if (event.location, event.event_type) != (child.location, child.event_type)
                or (child.event_type == EventType.MOVE and not child.dest_path.startswith(event.dest_path))
            ]
            if conflicts:
                logger.error('Detected {} conflicts for folder {}. ({})'.format(len(conflicts), event.src_path, [x.context for x in conflicts]))
            else:
                td[parts] = event
                directories.remove(event)

        for child in td.children():
            if child.is_directory:
                del td[child.src_path.split(os.path.sep)[:-1]]
                directories.append(child)

        directories = sorted(directories, key=lambda x: getattr(x, 'dest_path', x.src_path).count(os.path.sep))

        for operation in itertools.chain(resolutions, (event.operation() for event in directories), (event.operation() for event in td.children())):
            OperationWorker().put(operation)

        OperationWorker().join_queue()


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

    def children(self, *, keys=None):
        try:
            sub_dict = self[keys] if keys is not None else self._inner
        except KeyError:
            return []
        return flatten(sub_dict, [])

    def __contains__(self, keys):
        try:
            self[keys]
        except KeyError:
            return False
        return True

    def __delitem__(self, keys):
        self[keys] = {}
