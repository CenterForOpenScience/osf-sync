class OSFOfflineException(Exception):
    """ Base exception from which all others should inherit
    """
    def __init__(self, msg=None):
        self.message = msg

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.message)

    __str__ = __repr__

class AuthError(OSFOfflineException):
    """Generic authentication error while connecting to the OSF"""
    pass


class TwoFactorRequiredError(AuthError):
    """Headers on request indicate that a two-factor authentication code must be provided to authenticate"""
    pass


class InvalidPathError(OSFOfflineException):
    pass


class NodeNotFound(OSFOfflineException):
    pass
