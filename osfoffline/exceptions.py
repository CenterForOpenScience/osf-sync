class OSFOfflineException(Exception):
    """ Base exception from which all others should inherit
    """
    def __init__(self, msg=None):
        self.message = msg

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.message)

    __str__ = __repr__

class AuthError(OSFOfflineException):
    pass


class InvalidPathError(OSFOfflineException):
    pass


class NodeNotFound(OSFOfflineException):
    pass