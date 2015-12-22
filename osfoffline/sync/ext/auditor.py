from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import logging
import os
from pathlib import Path

from osfoffline import settings
from osfoffline.client.osf import OSFClient
from osfoffline.database import Session
from osfoffline.database.models import Node, File
from osfoffline.tasks import operations
from osfoffline.tasks.operations import OperationContext
from osfoffline.utils import hash_file
from osfoffline.utils.authentication import get_current_user


logger = logging.getLogger(__name__)


class Location(Enum):
    LOCAL = 0
    REMOTE = 1


class EventType(Enum):
    CREATE = 0
    DELETE = 1
    MOVE = 2
    UPDATE = 3


# Meant to emulate the watchdog FileSystemEvent
# May want to subclass in the future
class ModificationEvent:

    def __init__(self, location, event_type, contexts, src_path, dest_path=None):
        if dest_path:
            self.dest_path = dest_path
        self.location = location
        self.src_path = src_path
        self.event_type = event_type
        self.contexts = contexts
        self.context = contexts[0]
        self.is_directory = src_path.endswith(os.path.sep) or not src_path

    def operation(self):
        location = Location.LOCAL if self.location == Location.REMOTE else Location.REMOTE
        return getattr(
            operations,
            ''.join([
                location.name.capitalize(),
                self.event_type.name.capitalize(),
                'Folder' if self.is_directory else 'File'
            ])
        )(*self.contexts)

    @property
    def key(self):
        return (self.event_type, self.src_path, self.is_directory)

    def __eq__(self, event):
        return self.__class__ == event.__class__ and self.key == event.key

    def __ne__(self, event):
        return self.key != event.key

    def __hash__(self):
        return hash(self.key)


class Auditor:

    def __init__(self):
        self.user_folder = get_current_user().folder + os.path.sep

    def audit(self):
        db_map = self.collect_all_db()
        remote_map = self.collect_all_remote()
        local_map = self.collect_all_local(db_map)

        def context_for(paths):
            if not isinstance(paths, tuple):
                paths = (paths, )
            return [OperationContext(self.user_folder / Path(path),
                                     db_map.get(path, (None, ))[-1],
                                     remote_map.get(path, (None, ))[-1])
                    for path in paths]

        diffs = {
            Location.LOCAL: self._diff(local_map, db_map),
            Location.REMOTE: self._diff(remote_map, db_map),
        }

        modifications = {}
        for location, changes in diffs.items():
            modifications[location] = {}
            for event_type in EventType:
                for change in changes[event_type]:
                    if not isinstance(change, tuple):
                        change = (change, )
                    for s in change:
                        parts = s.split(os.path.sep)
                        while len(parts) > 2:
                            parts.pop(-1)
                            path = os.path.sep.join(parts + [''])
                            if path not in modifications[location]:
                                modifications[location][path] = ModificationEvent(location, EventType.UPDATE, context_for(path), path)
                        modifications[location][s] = ModificationEvent(location, event_type, context_for(change), *change)
        return modifications[Location.LOCAL], modifications[Location.REMOTE]

    def collect_all_db(self):
        return {db.path.replace(self.user_folder, ''): (db.id, db.sha256, db)
                for db in Session().query(File)}

    def collect_all_remote(self):
        ret = {}
        with ThreadPoolExecutor(max_workers=5) as tpe:
            for node in Session().query(Node):
                try:
                    remote_node = OSFClient().get_node(node.id)
                except Exception as e:
                    # If the node can't be reached, skip auditing of this project and go on to the next node
                    # TODO: The client should be made smart enough to check return code before parsing and yield a custom exception
                    # TODO: The user should be notified about projects that failed to sync, and given a way to deselect them
                    logger.exception(e)
                    continue
                remote = remote_node.get_storage(id='osfstorage')
                rel_path = os.path.join('{} - {}'.format(node.title, node.id), settings.OSF_STORAGE_FOLDER)
                # TODO: Use futures to catch exceptions in processing a node
                tpe.submit(self._collect_node_remote, remote, ret, rel_path, tpe)
            tpe._work_queue.join()
        return ret

    def _collect_node_remote(self, root, acc, rel_path, tpe):
        if root.parent:
            rel_path = os.path.join(rel_path, root.name)

        acc[rel_path + os.path.sep] = (root.id, None if root.is_dir else root.extra['hashes']['sha256'], root)

        for child in root.get_children():
            # TODO replace with pattern matching
            if child.name in settings.IGNORED_NAMES:
                continue
            if child.kind == 'folder':
                #self._collect_node_remote(child, acc, rel_path, tpe)
                tpe.submit(self._collect_node_remote, child, acc, rel_path, tpe)
            else:
                acc[os.path.join(rel_path, child.name)] = (child.id, child.extra['hashes']['sha256'], child)
        tpe._work_queue.task_done()
        #return acc

    def collect_all_local(self, db_map):
        ret = {}
        for node in Session().query(Node):
            node_path = Path(os.path.join(node.path, settings.OSF_STORAGE_FOLDER))
            self._collect_node_local(node_path, ret, db_map)
        return ret

    def _collect_node_local(self, root, acc, db_map):
        rel_path = str(root).replace(self.user_folder, '') + os.path.sep
        acc[rel_path] = (db_map.get(rel_path, (None, ))[0], None, rel_path)

        for child in root.iterdir():
            # TODO replace with pattern matching
            if child.name in settings.IGNORED_NAMES:
                continue
            if child.is_dir():
                self._collect_node_local(child, acc, db_map)
            else:
                rel_path = str(child).replace(self.user_folder, '')
                acc[rel_path] = (db_map.get(rel_path, (None, ))[0], hash_file(child), rel_path)
        return acc

    def _diff(self, source, target):
        # source == snapshot
        # target == ref
        id_target = {v[0]: k for k, v in target.items()}
        id_source = {v[0]: k for k, v in source.items()}

        created = set(source.keys()) - set(target.keys())
        deleted = set(target.keys()) - set(source.keys())

        for i in set(source.keys()) & set(target.keys()):
            if source[i][0] != target[i][0]:
                created.add(i)
                deleted.add(i)

        moved = set()
        for path in set(deleted):
            id = target[path][0]
            if id in id_source:
                deleted.remove(path)
                moved.add((path, id_source[id]))

        for path in set(created):
            id = source[path][0]
            if id in id_target:
                created.remove(path)
                moved.add((id_target[id], path))

        modified = set()
        for path in set(target.keys()) & set(source.keys()):
            if target[path][1] != source[path][1]:
                modified.add(path)

        for (src, dest) in moved:
            if target[src][1] != source[dest][1]:
                modified.add(src)

        return {
            EventType.CREATE: created,
            EventType.DELETE: deleted,
            EventType.MOVE: moved,
            EventType.UPDATE: modified,
        }
