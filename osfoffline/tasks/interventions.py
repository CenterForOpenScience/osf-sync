import abc
import enum
import asyncio

from osfoffline.tasks import operations


class Decision(enum.Enum):
    MINE = 0
    THEIRS = 1
    KEEP_BOTH = 2
    MERGE = 3


# Use the naming convention <LOCATION><ACTION>
# IE: RemoteCreated, BothDeleted, etc
class BaseIntervention(abc.ABC):

    @abc.abstractmethod
    @asyncio.coroutine
    def resolve(self, decision):
        raise NotImplementedError

    def __init__(self, auditor):
        self.auditor = auditor


class LocalFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.THEIRS

    def __init__(self, auditor):
        super().__init__(auditor)
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteDeleteFile(self.auditor.remote))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.LocalCreateFile(self.auditor.remote,
                                                                                   self.auditor.node))
        else:
            raise ValueError("Unknown decision")


class RemoteFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, auditor):
        super().__init__(auditor)
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteCreateFile(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.LocalDeleteFile(self.auditor.local))
        else:
            raise ValueError("Unknown decision")


class RemoteLocalFileConflict(BaseIntervention):

    DEFAULT_DECISION = Decision.KEEP_BOTH

    def __init__(self, auditor):
        super().__init__(auditor)
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS, Decision.KEEP_BOTH)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteUpdateFile(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.LocalUpdateFile(self.auditor.remote))
        elif decision == Decision.KEEP_BOTH:
            yield from self.auditor.operation_queue.put(operations.LocalKeepFile(self.auditor.local))
            yield from self.auditor.operation_queue.put(operations.LocalCreateFile(self.auditor.remote,
                                                                                   self.auditor.node))
        else:
            raise ValueError("Unknown decision")


class RemoteFolderDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, auditor, events):
        super().__init__(auditor)
        self.changed = 0
        self.deleted = 0

        for event in events:
            if isinstance(event, (operations.LocalDeleteFile, operations.LocalDeleteFolder)):
                self.deleted += 1
            else:
                self.changed += 1

        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        # TODO: Validate logic
        # TODO Add all child tasks to queue
        # TODO implement the MERGE Option
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteCreateFolder(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.LocalDeleteFolder(self.auditor.local))
        else:
            raise ValueError("Unknown decision")
