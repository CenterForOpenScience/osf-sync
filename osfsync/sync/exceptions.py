from osfsync import exceptions


class SyncException(exceptions.OSFSyncException):
    pass


class FolderNotInFileSystem(SyncException):
    pass
