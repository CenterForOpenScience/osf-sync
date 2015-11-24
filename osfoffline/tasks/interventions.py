import abc
import enum


class Decision(enum.Enum):
    MINE = 0
    THEIRS = 1
    KEEP_BOTH = 2


# Use the naming convention <LOCATION><ACTION>
# IE: RemoteCreated, BothDeleted, etc
class BaseIntervention(abc.ABC):

    DEFAULT_DECISION = Decision.KEEP_BOTH

    @abc.abstractmethod
    def resolve(self, decision):
        raise NotImplementedError

    def __init__(self, auditor):
        self.auditor = auditor


class BothUpdated(BaseIntervention):
    pass


class BothCreated(BaseIntervention):
    pass


class RemoteDeleted(BaseIntervention):
    pass
