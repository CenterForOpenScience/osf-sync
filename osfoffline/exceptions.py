__author__ = 'himanshu'


# Preferences
class Preferences(Exception):
    pass


# TrayIcon
class TrayIcon(Exception):
    pass


# Poll
class Poll(Exception):
    pass


# Event Handler
class EventHandler(Exception):
    pass


# Items
class ItemError(Exception):
    pass


class ItemNotInDB(ItemError):
    pass


class ItemNotInFileSystem(ItemError):
    pass


class FileNotinDB(ItemNotInDB):
    pass


class FolderNotInDB(ItemNotInDB):
    pass


class NodeNotinDB(ItemNotInDB):
    pass


class FileNotInFileSystem(ItemNotInFileSystem):
    pass


class FolderNotInFileSystem(ItemNotInFileSystem):
    pass


class NodeNotInFileSystem(ItemNotInFileSystem):
    pass


# OSF ERROR
class OSFError(Exception):
    pass


class OSFAuthError(OSFError):
    pass


class NodeNoAccess(OSFAuthError):
    pass


class FileNoAccess(OSFAuthError):
    pass


class AlreadyOnOSFError(OSFError):
    pass


class NewFileAlreadyOnOSF(AlreadyOnOSFError):
    pass


class NewNodeAlreadyOnOSF(AlreadyOnOSFError):
    pass


class NotFound(OSFError):
    pass


class FileNotFound(NotFound):
    pass


class NodeNotFound(NotFound):
    pass


class StateError(Exception):
    pass


class LocalAndRemoteNone(StateError):
    pass

# Path
class PathError(Exception):
    pass

class InvalidPathError(PathError):
    pass
