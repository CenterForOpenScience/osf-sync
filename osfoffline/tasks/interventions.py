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
            yield from self.auditor.operation_queue.put(operations.DeleteFile(self.auditor.remote))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.DownloadFile(self.auditor.remote))
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
            yield from self.auditor.operation_queue.put(operations.UploadFile(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.DownloadFile(self.auditor.remote))
        elif decision == Decision.KEEP_BOTH:
            yield from self.auditor.operation_queue.put(operations.KeepFile(self.auditor.local))
            yield from self.auditor.operation_queue.put(operations.DownloadFile(self.auditor.remote))
        else:
            raise ValueError("Unknown decision")


class RemoteFolderDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, auditor, events):
        super().__init__(auditor)
        self.changed = 0
        self.deleted = 0

        for event in events:
            if isinstance(event, (operations.DeleteFile, operations.DeleteFolder)):
                self.deleted += 1
            else:
                self.changed += 1

        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        # TODO: Validate logic
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.UploadFolder(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.DeleteFolder(self.auditor.local))
        else:
            raise ValueError("Unknown decision")
