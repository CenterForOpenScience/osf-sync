__author__ = 'himanshu'

"""
                                                           |-> SyncStateError
                                                           |
SyncStateNotSetup -> SyncStateNotRun ->  SyncStateIdle-----
                                                           |
                                                           |-> SyncStatePending -> SyncStateSyncing
"""

class SyncState(object):
    pass



class SyncStateNotSetup(SyncState):
    pass
class SyncStateSyncNotRun(SyncState):
    pass
class SyncStateIdle(SyncState):
    pass
class SyncStateError(SyncState):
    pass
class SyncStatePending(SyncState):
    pass
class SyncStateSyncing(SyncState):
    pass
