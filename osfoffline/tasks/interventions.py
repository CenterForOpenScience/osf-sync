import abc
import enum
import logging
import threading

from osfoffline.sync.ext.auditor import EventType
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

    def __init__(self, local, remote):
        self.local = local
        self.remote = remote
        self.decision = None
        self.event = threading.Event()
        logger.warning('Created Intervention {}'.format(self.__class__.__name__))

    def set_result(self, decision):
        logger.info('Resolved Intervention {}: {}'.format(self.__class__.__name__, decision))
        self.decision = decision
        self.event.set()

    @abc.abstractmethod
    def resolve(self):
        raise NotImplementedError


class LocalFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.THEIRS

    def __init__(self, auditor):
        super().__init__(auditor)
        self.title = 'Local File Deleted'
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    def resolve(self):
        if self.decision == Decision.MINE:
            return [operations.RemoteDeleteFile(self.remote.context)]
        elif self.decision == Decision.THEIRS:
            return [
                operations.DatabaseDeleteFile(self.remote.context),
                operations.LocalCreateFile(self.remote.context),
            ]
        raise ValueError('Unknown decision')


class LocalFolderDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.THEIRS

    def __init__(self, local, remote, remote_children):
        super().__init__(local, remote)
        self.title = 'Local Folder Deleted'
        self.description = 'The Local Folder \'{}\' was Deleted, however it still exists in the Remote Project {}.\n' \
            '\n' \
            'The Remote Folder contains {} objects.'.format(self.remote.db.path, self.remote.node.id, len(remote_children))
        self.options = (Decision.MINE, Decision.THEIRS)

    def resolve(self):
        if self.decision == Decision.MINE:
            return [operations.RemoteDeleteFolder(self.remote)]
        elif self.decision == Decision.THEIRS:
            return [operations.LocalCreateFolder(self.remote)]
        raise ValueError('Unknown decision')


class RemoteFileDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, local, remote):
        super().__init__(local, remote)
        self.title = 'Remote File Deleted'
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS)

    def resolve(self):
        if self.decision == Decision.MINE:
            return [operations.RemoteCreateFile(self.local)]
        elif self.decision == Decision.THEIRS:
            return [operations.LocalDeleteFile(self.local)]
        raise ValueError('Unknown decision')


class RemoteLocalFileConflict(BaseIntervention):

    DEFAULT_DECISION = Decision.KEEP_BOTH

    def __init__(self, local, remote):
        super().__init__(local, remote)
        self.title = 'Remote Local File Conflict'
        self.description = 'This is the description'
        self.options = (Decision.MINE, Decision.THEIRS, Decision.KEEP_BOTH)

    def resolve(self):
        if self.decision == Decision.MINE:
            if self.local.event_type == EventType.CREATE and self.remote.event_type == EventType.CREATE:
                return [
                    operations.DatabaseCreateFile(self.local.context),
                    operations.RemoteUpdateFile(self.local.context),
                ]
            return [operations.RemoteUpdateFile(self.local.context)]
        elif self.decision == Decision.THEIRS:
            if self.local.event_type == EventType.CREATE and self.remote.event_type == EventType.CREATE:
                return [
                    operations.DatabaseCreateFile(self.remote.context),
                    operations.LocalUpdateFile(self.remote.context),
                ]
            return [operations.LocalUpdateFile(self.remote.context)]
        elif self.decision == Decision.KEEP_BOTH:
            return [
                operations.LocalKeepFile(self.local.context),
                operations.LocalCreateFile(self.remote.context),
            ]
        raise ValueError('Unknown decision')


class RemoteFolderDeleted(BaseIntervention):

    DEFAULT_DECISION = Decision.MINE

    def __init__(self, local, remote, events):
        super().__init__(local, remote)
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

    def resolve(self):
        # TODO: Validate logic
        # TODO Add all child tasks to queue
        # TODO implement the MERGE Option
        if self.decision == Decision.MINE:
            return [operations.RemoteCreateFolder(self.local)]
        elif self.decision == Decision.THEIRS:
            return [operations.LocalDeleteFolder(self.local)]
        raise ValueError('Unknown decision')


class Intervention(metaclass=Singleton):

    def set_callback(self, cb):
        self.cb = cb

    def resolve(self, intervention):
        self.cb(intervention)
        intervention.event.wait()
        return intervention.resolve()
