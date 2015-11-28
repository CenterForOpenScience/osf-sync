import abc
import enum
import asyncio

from osfoffline.tasks import events


class Decision(enum.Enum):
    MINE = 0
    THEIRS = 1
    KEEP_BOTH = 2
    MERGE = 3


# Use the naming convention <LOCATION><ACTION>
# IE: RemoteCreated, BothDeleted, etc
class BaseIntervention(abc.ABC):

    @abc.abstractmethod
    def get_options(self):
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def resolve(self, decision):
        raise NotImplementedError

    def __init__(self, auditor):
        self.auditor = auditor


class LocalFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.THEIRS

    def get_options(self):
        return (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.queue.put(events.DeleteFile(self.auditor.remote))
        elif decision == Decision.THEIRS:
            yield from self.auditor.queue.put(events.DownloadFile(self.auditor.remote))
        else:
            raise ValueError("Unknown decision")


class RemoteLocalFileConflict(BaseIntervention):

    DEFAULT_DECISION = Decision.KEEP_BOTH

    def get_options(self):
        return (Decision.MINE, Decision.THEIRS, Decision.KEEP_BOTH)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.queue.put(events.UploadFile(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.queue.put(events.DownloadFile(self.auditor.remote))
        elif decision == Decision.KEEP_BOTH:
            yield from self.auditor.queue.put(events.KeepFile(self.auditor.local))
            yield from self.auditor.queue.put(events.DownloadFile(self.auditor.remote))
        else:
            raise ValueError("Unknown decision")


class RemoteFolderDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, auditor, events):
        super().__init__(auditor)
        self.changed = 0
        self.deleted = 0

        for event in events:
            if isinstance(event, (events.DeleteFile, events.DeleteFolder)):
                self.deleted += 1
            else:
                self.changed += 1

    def get_options(self):
        return (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        # TODO: Validate logic
        if decision == Decision.MINE:
            yield from self.auditor.queue.put(events.UploadFolder(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.queue.put(events.DeleteFolder(self.auditor.local))
        else:
            raise ValueError("Unknown decision")
