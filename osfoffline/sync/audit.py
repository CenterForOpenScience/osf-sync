import os
import abc
import asyncio
import hashlib

from sqlalchemy.orm.exc import NoResultFound

from osfoffline import settings
from osfoffline.client.osf import Node
from osfoffline.database_manager.db import session
from osfoffline.database_manager.models import File
from osfoffline.tasks import interventions
from osfoffline.tasks import operations
from osfoffline.utils.path import ProperPath


class BaseAuditor(abc.ABC):

    @abc.abstractmethod
    @asyncio.coroutine
    def _remote_changed(self):
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def _local_changed(self):
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def _on_both_changed(self):
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def _on_remote_changed(self):
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def _on_local_changed(self):
        raise NotImplementedError

    def __init__(self, node, operation_queue, intervention_queue, remote, local, *, decision=None, initial=False):
        """
        :param Node node: Database object describing a node
        :param OperationsQueue operation_queue: Where to store operations that can be performed automatically
        :param InterventionQueue intervention_queue: Where to store actions that require a user decision
        :param remote: The response from the server describing a remote node, file, or folder
        :type remote: StorageObject
        :type remote: None
        :param local: Path to the local file or folder
        :type local: ProperPath
        :type local: None
        :param Enum decision: The enumeration option representing a user decision
        :param bool initial: Whether this represents an initial "offline mode" sync (before filesystem observer active)
        """
        self.is_initial = initial

        self.node = node
        self.operation_queue = operation_queue
        self.intervention_queue = intervention_queue
        self.decision = decision

        self.local = local
        self.remote = remote
        self.db = None  # Database object representing one specific local (or remote) file

        if isinstance(remote, Node):
            return

        try:
            if self.remote:
                self.db = session.query(File).filter(
                    File.is_folder == self.remote.is_dir,
                    File.osf_id == self.remote.id
                ).one()
            else:
                self.db = next((
                    f for f in
                    session.query(File).filter(File.is_folder == self.local.is_dir, File.name == self.local.name)
                    if f.path == self.local.full_path
                ))
        except (NoResultFound, StopIteration):
            pass

    @asyncio.coroutine
    def audit(self):
        remote_changed = yield from self._remote_changed()
        local_changed = yield from self._local_changed()

        if remote_changed and local_changed:
            return (yield from self._on_both_changed())
        elif remote_changed:
            return (yield from self._on_remote_changed())
        elif local_changed:
            return (yield from self._on_local_changed())
        return None

    @asyncio.coroutine
    def _handle_sync_decision(self, intervention):
        if self.decision is not None:
            yield from intervention.resolve(self.decision)
        yield from self.intervention_queue.put(intervention)
        return True  # TODO: Replace w/ enum


class FileAuditor(BaseAuditor):

    @asyncio.coroutine
    def _remote_changed(self):
        if not self.remote and not self.db:
            return False
        if self.remote and self.db:
            return self.remote.extra['hashes']['sha256'] == self.db.sha256
        return True

    @asyncio.coroutine
    def _local_changed(self):
        if not self.local and not self.db:
            return False
        if self.local and self.db:
            if self.is_initial:
                return not (os.path.getsize(self.local.full_path) == self.db.size and self.db.sha256 == (yield from self._get_local_sha256()))
            else:
                # TODO optimize. No need to hash the file while in "Online mode" can just check date modified
                return not (os.path.getsize(self.local.full_path) == self.db.size and self.db.sha256 == (yield from self._get_local_sha256()))
        return True

    @asyncio.coroutine
    def _on_both_changed(self):
        if not self.remote and not self.local:
            return (yield from self.operation_queue.put(operations.DatabaseDeleteFile(self.db)))
        elif self.remote and not self.local:
            return (yield from self._handle_sync_decision(interventions.LocalFileDeleted(self)))
        elif not self.remote and self.local:
            return (yield from self._handle_sync_decision(interventions.RemoteFileDeleted(self)))
        elif self.remote.extra['hashes']['sha256'] == (yield from self._get_local_sha256()):
            return (yield from self.operation_queue.put(operations.DatabaseCreateFile(self.remote)))
        return (yield from self._handle_sync_decision(interventions.RemoteLocalFileConflict(self)))

    @asyncio.coroutine
    def _on_remote_changed(self):
        # Assumption: self.db is equivalent to self.local and was at one point in sync with self.remote.
        if not self.remote:
            # TODO: Need remote un-delete feature w/ user notification.
            # File has been deleted on the remote and not changed locally.
            return (yield from self.operation_queue.put(operations.RemoteDeleteFile(self.local)))
        if not self.local:
            # File has been updated remotely, we don't have it locally.
            return (yield from self.operation_queue.put(operations.LocalCreateFile(self.remote,
                                                                                   self.node)))
            # File has been updated remotely, we have an old version.
        return (yield from self.operation_queue.put(operations.LocalUpdateFile(self.remote)))

    @asyncio.coroutine
    def _on_local_changed(self):
        # Assumption: Either this is the initial sync, or watchdog missed this file somehow
        if not self.local:
            # File has been deleted locally, and remote exists.
            return (yield from self._handle_sync_decision(interventions.LocalFileDeleted(self)))
        if not self.remote:
            # File has been modified locally, and remote does not exist.
            return (yield from self.operation_queue.put(operations.RemoteCreateFile(self.local)))
            # File has been modified locally, and remote has not changed.
        return (yield from self.operation_queue.put(operations.RemoteUpdateFile(self.local)))

    @asyncio.coroutine
    def _get_local_sha256(self, *, chunk_size=64*1024):
        if not hasattr(self, '__local_sha'):
            s = hashlib.sha256()
            with open(self.local.full_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    s.update(chunk)
                    yield from asyncio.sleep(0)
            self.__local_sha = s.hexdigest()
        return self.__local_sha


class FolderAuditor(BaseAuditor):

    @asyncio.coroutine
    def audit(self):
        # Assumptions: should always return None, a truthy value indicates an intervention was issued for this junction.
        if not (yield from super().audit()):
            # Continue crawling
            return (yield from self.crawl())

    @asyncio.coroutine
    def _remote_changed(self):
        return (self.remote and not self.db) or (not self.remote and self.db)

    @asyncio.coroutine
    def _local_changed(self):
        return (self.remote and not self.db) or (not self.remote and self.db)

    @asyncio.coroutine
    def _on_both_changed(self):
        if not self.remote and not self.local:
            # Remote and local do not exist but a database entry exists
            return (yield from self.operation_queue.put(operations.DatabaseDeleteFolder(self.db)))
        # Remote and local do exist but a database entry does not exist
        return (yield from self.operation_queue.put(operations.DatabaseCreateFolder(self.remote, self.node)))

    @asyncio.coroutine
    def _on_remote_changed(self):
        # Assumption: self.db is equivalent to self.local and was at one point in sync with self.remote.
        if not self.remote:
            # TODO: Need remote un-delete feature, one can recursively verify no modifications locally and perform deletion w/ user notification.
            # TODO: User will be prompted for folder deletions
            # Folder has been deleted on the remote, ask for user intervention
            op_queue = asyncio.Queue()

            yield from self.crawl(operation_queue=op_queue, decision=interventions.Decision.MERGE)

            changed = False
            q = list(op_queue._queue)
            for event in q:
                if not isinstance(event, (operations.DeleteFile, operations.DeleteFolder)):
                    changed = True
                    break

            if changed or len(q) > settings.LOCAL_DELETE_THRESHOLD:
                # TODO: Short circut child crawl
                return (yield from self._handle_sync_decision(interventions.RemoteFolderDeleted(self, q)))
            return (yield from self.operation_queue.put(operations.LocalDeleteFolder(self.local)))
        # Folder has been created remotely, we don't have it locally.
        return (yield from self.operation_queue.put(operations.LocalCreateFolder(self.remote)))

    @asyncio.coroutine
    def _on_local_changed(self):
        if not self.local:
            # Folder has been deleted locally, and remote exists.
            return (yield from self._handle_sync_decision(interventions.LocalFolderDeleted(self)))
        # Folder has been created locally, and remote does not exist
        return (yield from self.operation_queue.put(operations.RemoteCreateFolder(self.local)))

    @asyncio.coroutine
    def crawl(self, *, operation_queue=None, decision=None):
        directory_list = {}

        if self.remote:
            for item in (yield from self._list_remote_dir()):
                directory_list[(item.name, item.is_dir)] = [item, None]

        if self.local:
            for item in self._list_local_dir():
                directory_list.setdefault((item.name, item.is_dir), [None, None])[1] = item

        auditors = []
        for (name, is_dir), (remote, local) in directory_list.items():
            auditors.append(self._child(operation_queue, remote, local, is_dir, decision=decision))

        yield from asyncio.gather(*[auditor.audit() for auditor in auditors])

    def _child(self, operation_queue, remote, local, is_dir, *, decision=None):
        cls = FolderAuditor if is_dir else FileAuditor

        return cls(
            self.node,
            operation_queue or self.operation_queue,
            self.intervention_queue,
            remote,
            local,
            decision=decision or self.decision,
            initial=self.is_initial
        )

    @asyncio.coroutine
    def _list_remote_dir(self):
        return (yield from self.remote.get_children())

    def _list_local_dir(self):
        if not self.local.full_path.startswith(self.node.path):
            raise Exception('wat')

        return [
            ProperPath(
                os.path.join(self.local.full_path, name),
                os.path.isdir(os.path.join(self.local.full_path, name))
            )
            for name in os.listdir(self.local.full_path)
            if name not in settings.IGNORED_NAMES
        ]
