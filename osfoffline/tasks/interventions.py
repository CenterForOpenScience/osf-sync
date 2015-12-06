import abc
import enum
import asyncio
import logging

from osfoffline.tasks import operations
from osfoffline.utils import Singleton


logger = logging.getLogger(__name__)


class Decision(enum.Enum):
    MINE = 0
    THEIRS = 1
    KEEP_BOTH = 2
    MERGE = 3


# Use the naming convention <LOCATION><ACTION>
# IE: RemoteCreated, BothDeleted, etc
class BaseIntervention(abc.ABC):

    def __init__(self, auditor):
        self.auditor = auditor
        self.future = asyncio.Future()
        logger.info('Created Intervention {}'.format(self.__class__.__name__))

    def set_result(self, decision):
        logger.info('Resolved Intervention {}: {}'.format(self.__class__.__name__, decision))
        self.future._loop.call_soon_threadsafe(self.future.set_result, decision)

    @abc.abstractmethod
    @asyncio.coroutine
    def resolve(self, decision):
        raise NotImplementedError


class LocalFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.THEIRS

    def __init__(self, auditor):
        super().__init__(auditor)
        self.title = 'Local File Deleted'
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteDeleteFile(self.auditor.remote))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.DatabaseDeleteFile(self.auditor.db))
            yield from self.auditor.operation_queue.put(operations.LocalCreateFile(self.auditor.remote, self.auditor.node))
        else:
            raise ValueError('Unknown decision')


class LocalFolderDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.THEIRS

    def __init__(self, auditor, remote_children):
        super().__init__(auditor)
        self.title = 'Local Folder Deleted'
        self.description = 'The Local Folder \'{}\' was Deleted, however it still exists in the Remote Project {}.\n' \
            '\n' \
            'The Remote Folder contains {} objects.'.format(self.auditor.db.path, self.auditor.node.id, len(remote_children))
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteDeleteFolder(self.auditor.remote))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.LocalCreateFolder(self.auditor.remote, self.auditor.node))
        else:
            raise ValueError('Unknown decision')


class RemoteFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, auditor):
        super().__init__(auditor)
        self.title = 'Remote File Deleted'
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    @asyncio.coroutine
    def resolve(self, decision):
        if decision == Decision.MINE:
            yield from self.auditor.operation_queue.put(operations.RemoteCreateFile(self.auditor.local))
        elif decision == Decision.THEIRS:
            yield from self.auditor.operation_queue.put(operations.LocalDeleteFile(self.auditor.local))
        else:
            raise ValueError('Unknown decision')


class RemoteLocalFileConflict(BaseIntervention):

    DEFAULT_DECISION = Decision.KEEP_BOTH

    def __init__(self, auditor):
        super().__init__(auditor)
        self.title = 'Remote Local File Conflict'
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
            yield from self.auditor.operation_queue.put(operations.LocalCreateFile(self.auditor.remote, self.auditor.node))
        else:
            raise ValueError('Unknown decision')


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

        self.title = 'Remote Folder Deleted'
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
            raise ValueError('Unknown decision')


class Intervention(metaclass=Singleton):
    thread_safe = True

    def set_callback(self, cb):
        self.cb = cb

    @asyncio.coroutine
    def resolve(self, intervention):
        yield from asyncio.get_event_loop().run_in_executor(None, self.cb, intervention)
        yield from intervention.future
        return intervention.future.result()
