from osfoffline import exceptions


class SyncException(exceptions.OSFOfflineException):
    pass


class FolderNotInFileSystem(SyncException):
    pass
