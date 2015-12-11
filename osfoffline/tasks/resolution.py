import asyncio
import os

from osfoffline.tasks import operations
from osfoffline.database import session
from osfoffline.sync.ext.auditor import EventType
from osfoffline.utils.authentication import get_current_user


def prompt_user(local, remote, local_events, remote_events):
    if local.context.db and remote.context.remote and local.context.db.sha256 == remote.context.remote.extra['hashes'].sha256:
        return db_create(local, remote, local_events, remote_events)
    return []


def upload_as_new(local, remote, local_events, remote_events):
    # session.remove(local.context.db)
    # local.context.db = None
    return [operations.RemoteCreateFile(local.context)]


def db_create(local, remote, local_events, remote_events):
    del local_events[local.src_path]
    del remote_events[remote.src_path]
    if local.is_directory:
        return [operations.DatabaseCreateFolder(remote.contexts[-1])]
    return [operations.DatabaseCreateFile(remote.context)]


def db_delete(local, remote, local_events, remote_events):
    if local.is_directory:
        return [operations.DatabaseDeleteFolder(remote.context)]
    return [operations.DatabaseDeleteFile(remote.context)]


def download_file(local, remote, local_events, remote_events):
    return [operations.LocalCreateFile(local.context)]


def create_folder(local, remote, local_events, remote_events):
    return [operations.LocalCreateFolder(local.context)]


# def upload_as_new(local, remote, local_event, remote_events):
#     session.remove(local.context.db)
#     local.context.db = None
#     return operations.RemoteCreateFile(local.context)

@asyncio.coroutine
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
            yield from lremote.operation().run()
        elif child.endswith(os.path.sep):
            yield from handle_move_src_update(llocal, lremote, local_events, remote_events)

    session.delete(local.context.db)
    session.commit()
    return True


def move_gate(event_src, event_dest):
    def gate(local, remote, *args, **kwargs):
        if local.src_path == remote.src_path:
            return event_src(local, remote, *args, **kwargs)
        return event_dest(local, remote, *args, **kwargs)
    return gate


# (is directory, local event type, remote event type)
RESOLUTION_MAP = {
    (False, EventType.CREATE, EventType.CREATE): prompt_user,
    (False, EventType.DELETE, EventType.DELETE): db_delete,
    (False, EventType.UPDATE, EventType.DELETE): upload_as_new,
    (False, EventType.CREATE, EventType.MOVE): move_gate(None, prompt_user),
    (False, EventType.DELETE, EventType.MOVE): move_gate(lambda l,r,*_:[], download_file),
    (False, EventType.UPDATE, EventType.MOVE): move_gate('MoveThenUploadAsNew', prompt_user),
    (False, EventType.DELETE, EventType.UPDATE): download_file,
    (False, EventType.UPDATE, EventType.UPDATE): prompt_user,
    (True, EventType.CREATE, EventType.CREATE): db_create,
    (True, EventType.DELETE, EventType.DELETE): db_delete,
    (True, EventType.UPDATE, EventType.DELETE): 'PromptUserTheirs/Mine/Merge',
    (True, EventType.CREATE, EventType.MOVE): move_gate('CreateFolder', db_create),
    (True, EventType.DELETE, EventType.MOVE): lambda local, remote, local_events, remote_events: operations.LocalMoveFolder(remote.context),
    (True, EventType.UPDATE, EventType.MOVE): move_gate(handle_move_src_update, 'PromptUserMerge'),
    (True, EventType.DELETE, EventType.UPDATE): 'DownloadFolder',
    (True, EventType.UPDATE, EventType.UPDATE): lambda *args, **kwargs: [],
}
