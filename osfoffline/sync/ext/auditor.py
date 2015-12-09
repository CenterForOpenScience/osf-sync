import os
import asyncio
import hashlib

from pathlib import Path

from osfoffline import settings
from osfoffline.client.osf import OSFClient
from osfoffline.database import session
from osfoffline.database.models import Node, File
from osfoffline.utils.authentication import get_current_user


class ModificationEvent:

    def __init__(self, location, event_type, src_path, dest_path=None):
        if dest_path:
            self.dest_path = dest_path
        self.location = location
        self.src_path = src_path
        self.event_type = event_type
        self.is_dir = src_path.endswith(os.path.sep)


class Auditor:

    def __init__(self):
        self.user_folder = get_current_user().folder + os.path.sep

    @asyncio.coroutine
    def audit(self):
        db_map = self.collect_all_db()
        remote_map = yield from self.collect_all_remote()
        local_map = self.collect_all_local(db_map)

        local_diff = self._diff(local_map, db_map)
        remote_diff = self._diff(remote_map, db_map)

        events = []

        for location, changes in (('Local', local_diff), ('Remote', remote_diff)):
            for change_type in ('moved', 'modified', 'deleted', 'created'):
                for change in changes[change_type]:
                    if isinstance(change, tuple):
                        events.append(ModificationEvent(location, change_type, change[0], change[1]))
                    else:
                        events.append(ModificationEvent(location, change_type, change))

        changes = {}
        for event in events:
            if event.is_dir:
                continue
            tree = changes
            head, tail = os.path.split(event.src_path)
            for part in head.split(os.path.sep):
                tree = tree.setdefault(part, {})
            tree[tail] = event

        for event in events:
            if not event.is_dir:
                continue
            tree = changes
            head, tail = os.path.split(event.src_path)
            for part in head.split(os.path.sep):
                tree = tree.setdefault(part, {})
            tree[tail] = event


        return changes

    def collect_all_db(self):
        return {db.path.replace(self.user_folder, ''): (db.id, db.sha256) for db in session.query(File)}

    @asyncio.coroutine
    def collect_all_remote(self):
        ret = {}
        for node in session.query(Node):
            remote_node = yield from OSFClient().get_node(node.id)
            remote = yield from remote_node.get_storage(id='osfstorage')
            rel_path = os.path.join('{} - {}'.format(node.title, node.id), settings.OSF_STORAGE_FOLDER)
            yield from self._collect_node_remote(remote, ret, rel_path)
        return ret

    @asyncio.coroutine
    def _collect_node_remote(self, root, acc, rel_path):
        if root.parent:
            rel_path = os.path.join(rel_path, root.name)

        acc[rel_path + os.path.sep] = (root.id, None if root.is_dir else root.extra['hashes']['sha256'])

        for child in (yield from root.get_children()):
            # TODO replace with pattern matching
            if child.name in settings.IGNORED_NAMES:
                continue
            if child.kind == 'folder':
                yield from self._collect_node_remote(child, acc, rel_path)
            else:
                acc[os.path.join(rel_path, child.name)] = (child.id, child.extra['hashes']['sha256'])
        return acc

    def collect_all_local(self, db_map):
        ret = {}
        for node in session.query(Node):
            node_path = Path(os.path.join(node.path, settings.OSF_STORAGE_FOLDER))
            self._collect_node_local(node_path, ret, db_map)
        return ret

    def _collect_node_local(self, root, acc, db_map):
        rel_path = str(root).replace(self.user_folder, '') + os.path.sep
        acc[rel_path] = (db_map.get(rel_path, (None, ))[0], None)

        for child in root.iterdir():
            if child.is_dir():
                self._collect_node_local(child, acc, db_map)
            else:
                rel_path = str(child).replace(self.user_folder, '')
                acc[rel_path] = (db_map.get(rel_path, (None, ))[0], self._hash_file(child))
        return acc

    def _hash_file(self, path, chunk_size=64*1024):
        s = hashlib.sha256()
        with path.open(mode='rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                s.update(chunk)
        return s.hexdigest()

    def _diff(self, source, target):
        # source == snapshot
        # target == ref
        id_target = {v[0]: k for k, v in target.items()}
        id_source = {v[0]: k for k, v in source.items()}

        sha_target = {v[1]: k for k, v in target.items()}
        sha_source = {v[1]: k for k, v in source.items()}

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
            'created': created,
            'deleted': deleted,
            'moved': moved,
            'modified': modified
        }
