import os

from osfoffline.tasks import operations
from osfoffline.database import Session
from osfoffline.sync.ext.auditor import EventType
from osfoffline.tasks import interventions
from osfoffline.tasks.interventions import Intervention
from osfoffline.utils import hash_file


def prompt_user(local, remote, local_events, remote_events):
    # TODO Pass around pre computed SHAs
    if local.context.local and remote.context.remote and hash_file(local.context.local) == remote.context.remote.extra['hashes']['sha256']:
        return db_create(local, remote, local_events, remote_events)
    return Intervention().resolve(interventions.RemoteLocalFileConflict(local, remote))


def upload_as_new(local, remote, local_events, remote_events):
    # session.remove(local.context.db)
    # local.context.db = None
    return [operations.RemoteCreateFile(local.context)]


def db_create(local, remote, local_events, remote_events):
    if local.is_directory:
        return [operations.DatabaseCreateFolder(remote.contexts[-1])]
    return [operations.DatabaseCreateFile(remote.context)]


def db_delete(local, remote, local_events, remote_events):
    if local.is_directory:
        return [operations.DatabaseDeleteFolder(remote.context)]
    return [operations.DatabaseDeleteFile(remote.context)]


def db_update(local, remote, local_events, remote_events):
    if local.is_directory:
        return [operations.DatabaseUpdateFolder(remote.context)]
    return [operations.DatabaseUpdateFile(remote.context)]


def download_file(local, remote, local_events, remote_events):
    return [operations.LocalCreateFile(local.context)]


def create_folder(local, remote, local_events, remote_events):
    return [operations.LocalCreateFolder(local.context)]


# def upload_as_new(local, remote, local_event, remote_events):
#     session.remove(local.context.db)
#     local.context.db = None
#     return operations.RemoteCreateFile(local.context)


def handle_move_src_update(local, remote, local_events, remote_events):
    os.makedirs(remote.dest_path, exist_ok=True)
    local_events.pop(local.src_path)
    remote_events.pop(remote.src_path)
    remote_events.pop(remote.dest_path)

    for child in set(local_events.keys()) | set(remote_events.keys()):
        if not child.startswith(remote.src_path) and not child.startswith(remote.dest_path):
            continue
        if os.path.sep in child.replace(remote.src_path, '', 1).rstrip(os.path.sep) and os.path.sep in child.replace(remote.dest_path, '', 1).rstrip(os.path.sep):
            continue
        llocal, lremote = local_events.pop(child, None), remote_events.pop(child, None)
        if child not in (getattr(llocal, 'src_path', None), getattr(lremote, 'src_path', None)):
            continue
        if lremote and not llocal:
            lremote.operation().run()
        elif child.endswith(os.path.sep):
            handle_move_src_update(llocal, lremote, local_events, remote_events)

    Session().delete(local.context.db)
    Session().commit()
    return True


def move_to_conflict(local, remote, local_events, remote_events):
    # TODO Pass around pre computed SHAs
    if hash_file(local.context.local) == remote.contexts[1].remote.extra['hashes']['sha256']:
        if remote.contexts[0].db:
            if remote.is_directory:
                return [operations.DatabaseUpdateFolder(operations.OperationContext(
                    db=remote.contexts[0].db,
                    remote=remote.contexts[1].remote
                ))]
            else:
                return [operations.DatabaseUpdateFile(operations.OperationContext(
                    db=remote.contexts[0].db,
                    remote=remote.contexts[1].remote
                ))]
        return db_create(local, remote, local_events, remote_events)
    # Ask User
    return []


def move_gate(event_src, event_dest):
    def gate(local, remote, *args, **kwargs):
        if local.src_path == remote.src_path:
            return event_src(local, remote, *args, **kwargs)
        return event_dest(local, remote, *args, **kwargs)
    return gate


# File A modified locally. File B renamed to File B remotely
def fork_file(local, remote, local_events, remote_events):
    del remote_events[remote.dest_path]
    Session().remove(local.context.db)
    Session().commit()
    from osfoffline.sync.remote import RemoteSyncWorker
    RemoteSyncWorker().sync_now()


def remote_folder_delete(local, remote, local_events, remote_events):
    return Intervention().resolve(interventions.RemoteFolderDeleted(local, remote, local_events, remote_events))


# (is directory, local event type, remote event type)
RESOLUTION_MAP = {
    (False, EventType.CREATE, EventType.CREATE): prompt_user,
    (False, EventType.DELETE, EventType.DELETE): db_delete,
    (False, EventType.UPDATE, EventType.DELETE): upload_as_new,
    (False, EventType.CREATE, EventType.MOVE): move_gate(None, move_to_conflict),
    (False, EventType.DELETE, EventType.MOVE): move_gate(lambda *_: [], download_file),
    (False, EventType.UPDATE, EventType.MOVE): move_gate(fork_file, prompt_user),
    (False, EventType.DELETE, EventType.UPDATE): download_file,
    (False, EventType.UPDATE, EventType.UPDATE): prompt_user,
    (True, EventType.CREATE, EventType.CREATE): db_create,
    (True, EventType.DELETE, EventType.DELETE): db_delete,
    (True, EventType.UPDATE, EventType.DELETE): remote_folder_delete,
    (True, EventType.CREATE, EventType.MOVE): move_gate(create_folder, db_create),
    (True, EventType.DELETE, EventType.MOVE): lambda local, remote, *_: [remote.operation()],
    (True, EventType.UPDATE, EventType.MOVE): move_gate(handle_move_src_update, 'PromptUserMerge'),
    (True, EventType.DELETE, EventType.UPDATE): lambda *_: [],
    (True, EventType.UPDATE, EventType.UPDATE): lambda *_: [],
}
