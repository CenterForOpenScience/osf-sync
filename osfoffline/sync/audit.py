import os
import abc
import asyncio
import hashlib

from sqlalchemy.orm.exc import NoResultFound
from osfoffline.database_manager.db import session
from osfoffline.polling_osf_manager.osf_query import OSFQuery
# from osfoffline.database_manager.models import User, Node, File, Base
from osfoffline.database_manager.models import File
from osfoffline.client.osf import Node
from osfoffline.tasks import events
from osfoffline import settings
from osfoffline.utils.path import ProperPath
from osfoffline.sync import interventions
from osfoffline.exceptions.item_exceptions import InvalidItemType, FolderNotInFileSystem


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

    def __init__(self, node, queue, remote, local=None, intervention_cb=None, decision=None, state='OFFLINE'):
        self.state = state

        self.node = node
        self.queue = queue
        self.decision = decision
        self.intervention_cb = intervention_cb

        self.local = local
        self.remote = remote
        self.db = None

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
    def _get_decision(self, intervention):
        if self.decision is not None:
            return self.decision

        if self.intervention_cb:
            self.decision = yield from self.intervention_cb(intervention)
            return self.decision

        # TODO should we allow defaults?
        return intervention.DEFAULT_DECISION

    @asyncio.coroutine
    def _handle_sync_decision(self, intervention):
        yield from intervention.resolve((yield from self._get_decision(intervention)))


class FileAuditor(BaseAuditor):

    @asyncio.coroutine
    def _remote_changed(self):
        return (self.remote and self.db) and self.remote.extra['hashes']['sha256'] == self.db.sha256

    @asyncio.coroutine
    def _local_changed(self):
        if self.state == 'OFFLINE':
            if self.local and self.db:
                return not (os.path.getsize(self.local.full_path) == self.db.size and self.db.sha256 == (yield from self._get_local_sha256()))
            return True
        return False  # Online changes handled by watchdog

    @asyncio.coroutine
    def _on_both_changed(self):
        if not self.remote and not self.local:
            return (yield from self.queue.put(events.DatabaseFileDelete(self.db)))
        elif self.remote['extra']['hashes']['sha256'] == self._get_local_sha256():
            return (yield from self.queue.put(events.DatabaseFileCreate(self.remote)))
        return (yield from self._handle_sync_decision(interventions.RemoteLocalFileConflict(self)))

    @asyncio.coroutine
    def _on_remote_changed(self):
        # Assumption: self.db is equivalent to self.local and was at one point in sync with self.remote.
        if not self.remote:
            # TODO: Need remote un-delete feature w/ user notification.
            # File has been deleted on the remote and not changed locally.
            return (yield from self.queue.put(events.DeleteFile(self.local)))
        # File has been created remotely, we don't have it locally.
        return (yield from self.queue.put(events.DownloadFile(self.remote)))

    @asyncio.coroutine
    def _on_local_changed(self):
        # Assumption: we would never enter this method if self.state was not OFFLINE, no remote file changes have occurred.
        if not self.local:
            # File has been deleted locally, and remote exists.
            return (yield from self._handle_sync_decision(interventions.LocalFileDeleted(self)))
        # File has been modified locally, and remote has not changed.
        return (yield from self.queue.put(events.UploadFile(self.remote)))

    @asyncio.coroutine
    def _get_local_sha256(self, chunk_size=64*1024):
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
        yield from super().audit()

        # Continue crawling
        return (yield from self.crawl())

    @asyncio.coroutine
    def _remote_changed(self):
        return (self.remote and self.db)

    @asyncio.coroutine
    def _local_changed(self):
        if self.state == 'OFFLINE':
            return (self.local and self.db)
        return False  # Online changes handled by watchdog

    @asyncio.coroutine
    def _on_both_changed(self):
        if not self.remote and not self.local:
            return (yield from self.queue.put(events.DatabaseFolderDelete(self.db)))
        return (yield from self.queue.put(events.DatabaseFolderCreate(self.remote)))

    @asyncio.coroutine
    def _on_remote_changed(self):
        # Assumption: self.db is equivalent to self.local and was at one point in sync with self.remote.
        if not self.remote:
            # TODO: Need remote un-delete feature, one can recursively verify no modifications locally and perform deletion w/ user notification.
            # TODO: User will be prompted for folder deletions
            # Folder has been deleted on the remote, ask for user intervention
            queue = asyncio.Queue()

            yield from self.crawl(queue=queue, decision=interventions.Decision.MERGE)

            changed = False
            q = list(queue._queue)
            for event in q:
                if not isinstance(event, (events.DeleteFile, events.DeleteFolder)):
                    changed = True
                    break

            if changed or len(q) > settings.LOCAL_DELETE_THRESHOLD:
                return (yield from self._handle_sync_decision(interventions.RemoteFolderDeleted(self, q)))
            return (yield from self.queue.put(events.DeleteFolder(self.local)))
        # Folder has been created remotely, we don't have it locally.
        return (yield from self.queue.put(events.DownloadFolder(self.remote)))

    @asyncio.coroutine
    def _on_local_changed(self):
        # Assumption: we would never enter this method if self.state was not OFFLINE, no remote file changes have occurred.
        if not self.local:
            # File has been deleted locally, and remote exists.
            return (yield from self._handle_sync_decision(interventions.LocalFileDeleted(self)))
            return (yield from self.intervention_queue.put(intervensions.LocalFileDeleted(self)))
        # File has been modified locally, and remote has not changed.
        return (yield from self.queue.put(events.UploadFile(self.remote)))

    # @asyncio.coroutine
    # def audit(self):
    #     if self.db:
    #         if self.remote and self.local:  # (✓ remote, ✓ db, ✓ local)
    #             # Everything is okay continue one
    #             # Block left here for clarity
    #             pass
    #         elif self.remote:  # (✓ remote, ✓ db, X local)
    #             # Download Folder
    #             # Could prompt user
    #             # Note the return. Don't crawl further
    #             return (yield from self.queue.put(events.DownloadFolder(self.remote)))
    #         else:  # (X remote, ✓ db, ✓ local)
    #             # Prompt user
    #             # Could decide by ensuring nothing has changed in this folder or its subfolders
    #             # Or move to recycle bin, User could always restore if need be
    #             yield from self.queue.put((yield from self.handle_sync_decision(interventions.RemoteFolderDeleted(self))))
    #     else:
    #         if self.remote and self.local:  # (✓ remote, X db, ✓ local)
    #             # Create in database
    #             yield from self.queue.put(events.CreateDatabaseEntry(self.remote))
    #         elif self.remote:  # (✓ remote, X db, X local)
    #             # Create folder locally
    #             yield from self.queue.put(events.CreateLocalFolder(self.remote))
    #         elif self.local:  # (X remote, X db, ✓ local)
    #             # Ask whether to upload the folder or delete it
    #             # Or check logs :shrug:
    #             yield from self.queue.put((yield from self.handle_sync_decision(interventions.RemoteFolderDeleted(self))))
    #
    #     # Continue crawling
    #     return (yield from self.crawl())

    @asyncio.coroutine
    def crawl(self, queue=None, decision=None):
        directory_list = {}

        if self.remote:
            for item in (yield from self._list_remote_dir()):
                directory_list[(item.name, item.is_dir)] = [item, None]

        if self.local:
            for item in self._list_local_dir():
                directory_list.setdefault((item.name, item.is_dir), [None, None])[1] = item

        auditors = []
        for (name, is_dir), (remote, local) in directory_list.items():
            auditors.append(self._child(remote, local, is_dir, queue=queue, decision=decision))

        # done, pending = yield from asyncio.wait([auditor.audit() for auditor in auditors], return_when=asyncio.FIRST_EXCEPTION)
        # if pending:
        #     future = pending.pop()
        #     future.result()
        # assert not pending

        # tasks = [asyncio.ensure_future(auditor.audit()) for auditor in auditors]
        # [task.add_done_callback(self.handle_error) for task in tasks]

        yield from asyncio.gather(*[auditor.audit() for auditor in auditors])

        # yield from asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        # try:
        #     yield from asyncio.gather(*[auditor.audit() for auditor in auditors])
        # except Exception as ex:
        #     raise ex


    # def handle_error(self, future):
    #     if future.exception():
    #         raise future.exception()


    def _child(self, remote, local, is_dir, decision=None, queue=None):
        cls = FolderAuditor if is_dir else FileAuditor

        return cls(
            self.node,
            queue if queue else self.queue,
            remote,
            local,
            decision=decision if decision else self.decision,
            intervention_cb=self.intervention_cb,
        )

    @asyncio.coroutine
    def _list_remote_dir(self):
        if isinstance(self.remote, Node):
            return (yield from self.remote.get_storage('osfstorage'))
        return (yield from self.remote.get_children())

    def _list_local_dir(self):
        path = os.path.join(
            self.node.path,
            settings.OSF_STORAGE_FOLDER,
        )

        if self.local != '/':
            # Special case for the "root"
            path = os.path.join(path, self.local.full_path.lstrip('/'))

        return [
            ProperPath(
                os.path.join(path, name),
                os.path.isdir(os.path.join(path, name))
            )
            for name in os.listdir(path)
            if name not in settings.IGNORED_NAMES
        ]







    # @asyncio.coroutine
    # def _audit_in_db(self):
    #     # event = RemoteFileChanged
    #     # event = LocalFileChanged
    #     # event = RemoteLocalFileChanged
    #
    #
    #     if self.mode == 'OFFLINE':
    #         # Offline Mode is mean to bring the local db and local file system in sync.
    #         # A followup Online audit happening periodically via the pooling will download any new files.
    #         if self.remote and self.local:  # (✓ remote, ✓ db, ✓ local)
    #             local_sha = yield from self._get_local_sha256()
    #             if os.path.getsize(self.local.full_path) == self.db.size and self.db.sha256 == local_sha:
    #                 # File has not changed
    #                 return None
    #             if self.remote.extra['hashes']['sha256'] == self.db.sha256:
    #                 # Local file has been changed. Upload it
    #                 return (yield from self.queue.put(events.UploadFile(self.local)))
    #             # Prompt user
    #             return (yield from self.handle_sync_decision(interventions.RemoteLocalFileConflict(self)))
    #         elif self.remote:  # (✓ remote, ✓ db, X local)
    #             # Poller will re-download the file. Only persist deletes that happened whilst online
    #             # Or prompt user if they would like to delete the remote file
    #             return (yield from self.queue.put(events.DownloadFile(self.remote)))
    #         else:  # (X remote, ✓ db, X local)
    #             # File is gone. Delete from database
    #             return (yield from self.queue.put(events.DeleteDatabaseEntry(self.db)))
    #
    #     if self.mode == 'ONLINE':
    #         pass
    #
    # @asyncio.coroutine
    # def _audit_not_in_db(self):
    #     if self.remote and self.local:  # (✓ remote, X db, ✓ local)
    #         local_sha = yield from self._get_local_sha256()
    #         if os.path.getsize(self.local.full_path) == self.remote.size and self.remote['extra']['hashes']['sha256'] == local_sha:
    #             # Create entry in database
    #             return (yield from self.queue.put(events.CreateDatabaseEntry(self.remote)))
    #         if local_sha in [version['extra']['hashes']['sha256'] for version in self.remote.get_version()]:
    #             # File is an old version. Download the latest
    #             return (yield from self.queue.put(events.DownloadFile(self.remote)))
    #         # Prompt user. local and upstream have diverged
    #         return (yield from self.handle_sync_decision(interventions.RemoteLocalFileConflict(self)))
    #     elif self.remote:  # (X remote, X db, ✓ local)
    #         # File was created remotely. Download for the first time
    #         return (yield from self.queue.put(events.DownloadFile(self.remote)))
