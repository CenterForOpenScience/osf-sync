# TODO: migrate all exceptions to this file

class OSFOfflineException(Exception):
    """ Base exception from which all others should inherit
    """
    pass

class AuthError(OSFOfflineException):
    pass
