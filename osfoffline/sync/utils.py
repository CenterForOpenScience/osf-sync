import os
import itertools
from collections import OrderedDict
import itertools
import logging
import os
from pathlib import Path
import threading
from watchdog import events
from watchdog.events import (
    EVENT_TYPE_MOVED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MODIFIED,
    # DirModifiedEvent,
    # FileModifiedEvent,
    # DirMovedEvent,
    # FileMovedEvent,
)

from osfoffline.utils import is_ignored


logger = logging.getLogger(__name__)




class FileSystemEvent:

    @property
    def src_path(self):
        return self._watchdog_event.src_path

    @property
    def parts(self):
        return self.src_path.split(os.path.sep)

    @property
    def watchdog_event(self):
        return self._watchdog_event

    def __init__(self, root, watchdog):
        self._root = root
        self._watchdog_event = watchdog

    def combine(self, other):
        import ipdb; ipdb.set_trace()
        raise NotImplementedError


class ChainedEvent(FileSystemEvent):

    @property
    def root(self):
        return self._events[0].root

    @property
    def src_path(self):
        return self._events[0].src_path

    @property
    def parts(self):
        return self.src_path.split(os.path.sep)

    @property
    def watchdog_event(self):
        return [e.watchdog_event for e in self._events]

    def __init__(self, *events):
        assert len({e.src_path for e in events}) == 1, 'ChainedEvents must have matching paths'
        assert len({type(e) for e in events}) > 1, 'ChainedEvents must have differing event types'
        self._events = events

    def combine(self, other):
        raise NotImplementedError


class MoveMixin:

    @property
    def dest_path(self):
        return self._watchdog_event.dest_path

    @property
    def dest_parts(self):
        return self.dest_path.split(os.path.sep)

    def __init__(self, root, watchdog):
        self.is_destination = False
        super().__init__(root, watchdog)


### Folder Events ###

class FolderEvent(FileSystemEvent):

    @property
    def children(self):
        return self._children

    def __init__(self, root, watchdog_event):
        self._children = OrderedDict()
        super().__init__(root, watchdog_event)

    def insert(self, name, event):
        if not event:
            return self._children.pop(name, None)
        self._children[name] = event

    def get(self, name):
        return self._children[name]


class FolderModifiedEvent(FolderEvent):

    def combine(self, other):
        other._children = self.children
        # for child in self.children.values():
        #     other.insert(child)
        return other


class FolderCreatedEvent(FolderEvent):

    def combine(self, other):
        if isinstance(other, FolderDeletedEvent):
            return None
        if isinstance(other, FolderModifiedEvent):
            return self
        raise NotImplementedError


class FolderMovedEvent(MoveMixin, FolderEvent):

    @property
    def children(self):
        return OrderedDict()

    def __init__(self, root, watchdog):
        super().__init__(root, watchdog)
        self.destination = FolderMovedDestination(root, watchdog, self)

    def insert(self, name, event):
        if isinstance(event, (FileMovedEvent, FolderMovedEvent)):
            return super().insert(name, event)
        raise Exception((name, event, self))

class FolderMovedDestination(MoveMixin, FolderEvent):

    @property
    def src_path(self):
        return self._watchdog_event.dest_path

    def __init__(self, root, watchdog, source):
        super().__init__(root, watchdog)
        self.source = source


class FolderDeletedEvent(FolderEvent):

    @property
    def children(self):
        return OrderedDict()

    def insert(self, name, event):
        if isinstance(event, (FolderDeletedEvent, FileDeletedEvent)):
            return
        raise Exception('Attempted to insert {} into a deleted folder'.format(event))

    def combine(self, event):
        if isinstance(event, FolderCreatedEvent):
            return ChainedEvent(self, event)
        return super().combine(event)

### End Folder Events ###


### File Events ###

class FileEvent(FileSystemEvent):

    @property
    def children(self):
        raise TypeError('Files do not have children')

    def insert(self, name, event):
        raise TypeError('Files do not have children')

class FileCreatedEvent(FileEvent):

    def combine(self, event):
        if isinstance(event, FileModifiedEvent):
            return self
        if isinstance(event, FileDeletedEvent):
            return None
        if isinstance(event, FileMovedEvent):
            self._root.remove(event.destination)
            self._root.insert(events.FileCreatedEvent(event.dest_path))
            return None
        if isinstance(event, FileCreatedEvent):
            logger.warning('Attempted to combine two FileCreatedEvents {} and {}'.format(self, event))
            return self
        raise Exception(self, event)

class FileDeletedEvent(FileEvent):

    def combine(self, event):
        if isinstance(event, FileModifiedEvent):
            raise Exception('Modified deleted file')
        if isinstance(event, FileCreatedEvent):
            return FileModifiedEvent(self._root, events.FileModifiedEvent(self.src_path))
        if isinstance(event, FileMovedEvent):
            if event.src_path == self.src_path:
                return event
            raise Exception('NEED TO REMOVE DESTINATION')
        if isinstance(event, FileDeletedEvent):
            logger.warning('Attempted to combine two FileDeleteEvents {} and {}'.format(self, event))
            return self

class FileModifiedEvent(FileEvent):

    def combine(self, event):
        if isinstance(event, FileDeletedEvent):
            return event

        if isinstance(event, FileMovedDestination):
            return event

        if isinstance(event, FileMovedEvent):
            raise Exception('NEED TO REMOVE SRC')

        if isinstance(event, (FileModifiedEvent, FileCreatedEvent)):
            raise Exception('Impossible', self, event)


class FileMovedEvent(MoveMixin, FileEvent):

    def __init__(self, root, watchdog):
        super().__init__(root, watchdog)
        self.destination = FileMovedDestination(root, watchdog, self)

    def combine(self, event):
        if isinstance(event, FileMovedDestination):
            return event
        raise NotImplementedError

class FileMovedDestination(MoveMixin, FileEvent):

    @property
    def src_path(self):
        return self._watchdog_event.dest_path

    def __init__(self, root, watchdog, source):
        super().__init__(root, watchdog)
        self.source = source

    def combine(self, event):
        if isinstance(event, FileDeletedEvent):
            if self._root.get(*self.source.parts) is self.source:
                self._root.remove(self.source)
                self._root.insert(events.FileDeletedEvent(self.source.src_path))
            return None

        raise NotImplementedError

### End File Events ###


class EventConsolidator:

    WRAPPER_MAP = {
        (EVENT_TYPE_MOVED, True): FolderMovedEvent,
        (EVENT_TYPE_MOVED, False): FileMovedEvent,
        (EVENT_TYPE_DELETED, True): FolderDeletedEvent,
        (EVENT_TYPE_DELETED, False): FileDeletedEvent,
        (EVENT_TYPE_CREATED, True): FolderCreatedEvent,
        (EVENT_TYPE_CREATED, False): FileCreatedEvent,
        (EVENT_TYPE_MODIFIED, True): FolderModifiedEvent,
        (EVENT_TYPE_MODIFIED, False): FileModifiedEvent,
    }

    def wrap_watchdog(self, event):
        return self.WRAPPER_MAP[(event.event_type, event.is_directory)](self, event)

    @property
    def events(self):
        def flatten(folder, acc):
            for value in folder.children.values():
                if isinstance(value, FolderEvent):
                    flatten(value, acc)
                acc.append(value)
            return acc

        return sorted(
            sum((
                event.watchdog_event if isinstance(event.watchdog_event, list) else [event.watchdog_event]
                for event in flatten(self, [])
                if not isinstance(event, (FolderModifiedEvent, FileMovedDestination, FolderMovedDestination))
                and not is_ignored(event.src_path)
            ), []),
            key=lambda x: x.src_path.count(os.path.sep)
        )

    def __init__(self):
        self.children = OrderedDict()

    def clear(self):
        self.children = OrderedDict()

    def _insert(self, event):
        *path, name = event.parts
        child = self
        for part in path:
            child = child.children.setdefault(part, FolderModifiedEvent(self, part))
        if name not in child.children:
            return child.insert(name, event)
        conflicting = child.get(name)
        return child.insert(name, conflicting.combine(event))

    def remove(self, event):
        *path, name = event.parts
        child = self
        for part in path:
            child = child.children[part]
        del child.children[name]

    def get(self, *parts):
        *parts, name = parts
        child = self
        for part in parts:
            child = child.children[part]
        return child.children[name]

    def insert(self, event):
        event = self.wrap_watchdog(event)

        if isinstance(event, MoveMixin):
            self._insert(event.destination)
        return self._insert(event)
