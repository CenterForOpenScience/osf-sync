import abc

from sqlalchemy.orm.exc import NoResultFound
from osfoffline.database_manager.db import session
from osfoffline.polling_osf_manager.osf_query import OSFQuery
from osfoffline.database_manager.models import User, Node, File, Base
from osfoffline.exceptions.item_exceptions import InvalidItemType, FolderNotInFileSystem


class Auditor(abc.ABC):

    def audit(self):
        raise NotImplemented

    def __init__(self, node, queue, remote='/', local='/', intervention_cb=None, decision=None):
        self.node = node
        self.queue = queue
        self.decision = decision
        self.intervention_cb = intervention_cb

        self.local = local
        self.remote = remote

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
            self.db = None

    @asyncio
    def get_decision(self, intervention):
        if self.decision is not None:
            return self.decision

        if self.intervention_cb:
            self.decision = yield from self.intervention_cb(intervention)
            return self.decision

        # TODO should we allow defaults?
        return intervention.DEFAULT_DECISION

    @asyncio.coroutine
    def handle_sync_decision(self, intervention):
        return intervention.resolve((yield from self.get_decision(intervention)))


class FileAuditor(Auditor):

    @asyncio.coroutine
    def audit(self):
        if self.db:
            if self.remote and self.local:  # (✓ remote, ✓ db, ✓ local)
                if os.path.getsize(self.local.full_path) == self.db.size and self.db.sha256 == self._get_local_sha256():
                    # File has not changed
                    return None
                if self.remote.extra['hashes']['sha256'] == self.db.sha256:
                    # Local file has been changed. Upload it
                    return (yield from self.queue.put(events.UploadFile(self.local)))
                # Prompt user
                return (yield from self.handle_sync_decision(interventions.BothUpdated(self)))
            elif self.remote:  # (✓ remote, ✓ db, X local)
                # Poller will re-download the file. Only persist deletes that happened whilst online
                # Or prompt user if they would like to delete the remote file
                return (yield from self.queue.put(events.DownloadFile(self.remote)))
            else:  # (X remote, ✓ db, X local)
                # File is gone. Delete from database
                return (yield from self.queue.put(events.DeleteDatabaseEntry(self.db)))
        else:
            if self.remote and self.local:  # (✓ remote, X db, ✓ local)
                local_sha = self._get_local_sha256()
                if os.path.getsize(self.local.full_path) == self.remote.size and self.remote['extra']['hashes']['sha256'] == local_sha:
                    # Create entry in database
                    return (yield from self.queue.put(events.CreateDatabaseEntry(self.remote)))
                if local_sha in [version['extra']['hashes']['sha256'] for version in self.remote.get_version()]:
                    # File is an old version. Download the latest
                    return (yield from self.queue.put(events.DownloadFile(self.remote)))
                # Prompt user. local and upstream have diverged
                return (yield from self.handle_sync_decision(interventions.BothCreated(self)))
            elif self.remote:  # (X remote, X db, ✓ local)
                # File was created remotely. Download for the first time
                return (yield from self.queue.put(events.DownloadFile(self.remote)))

        # Should not be possible
        raise ValueError('Everything is None')


class FolderAuditor(Auditor):

    def child(self, remote, local, is_dir):
        cls = FolderAuditor if is_dir else FileAuditor

        return cls(
            self.node,
            remote,
            local,
            self.queue,
            decision=self.decision,
            user_intervention_cb=self.user_intervention_cb,
        )

    @asyncio.coroutine
    def audit(self):
        if self.db:
            if self.remote and self.local:  # (✓ remote, ✓ db, ✓ local)
                # Everything is okay continue one
                # Block left here for clarity
                pass
            elif self.remote:  # (✓ remote, ✓ db, X local)
                # Download Folder
                # Could prompt user
                # Note the return. Don't crawl further
                return (yield from self.queue.put(event.DownloadFolder(self.remote)))
            else:  # (X remote, ✓ db, ✓ local)
                # Prompt user
                # Could decide by ensuring nothing has changed in this folder or its subfolders
                # Or move to recycle bin, User could always restore if need be
                yield from self.queue.put((yield from self.handle_sync_decision(interventions.RemoteDeleted(self))))
        else:
            if self.remote and self.local:  # (✓ remote, X db, ✓ local)
                # Create in database
                yield from self.queue.put(event.CreateDatabaseEntry(self.remote))
            elif self.remote:  # (✓ remote, X db, X local)
                # Create folder locally
                yield from self.queue.put(event.CreateLocalFolder(self.remote))
            elif self.local:  # (X remote, X db, ✓ local)
                # Ask whether to upload the folder or delete it
                # Or check logs :shrug:
                yield from self.queue.put((yield from self.handle_sync_decision(interventions.RemoteDeleted(self))))

        # Continue crawling
        return (yield from self.crawl())

    @asyncio.coroutine
    def crawl(self):
        directory_list = {}

        if self.remote:
            for item in (yield from self._list_remote_dir()):
                directory_list[(item.name, item.is_dir)] = [None, remote]

        if self.local:
            for item in self._list_local_dir():
                directory_list.setdefault((item.name, item.is_dir), [None, None])[0] = item

        auditors = []
        for (name, is_dir), (remote, local) in directory_list.items():
            auditors.append(self.child(remote, local, is_dir))

        yield from asyncio.wait([auditor.audit() for auditor in auditors])

    @asyncio.coroutine
    def _list_remote_dir(self):
        if self.remote == '/':
            return (yield from self.node.get_storage('osfstorage'))
        return (yield from remote_folder.get_children())

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
