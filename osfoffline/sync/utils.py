import os
import logging
import itertools
import threading
from collections import OrderedDict
from pathlib import Path
from watchdog import events
from watchdog.events import (
    EVENT_TYPE_MOVED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MODIFIED,
)

from osfoffline.utils import is_ignored


logger = logging.getLogger(__name__)




class FileSystemEvent:
    COUNT = 0

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
        FileSystemEvent.COUNT += 1
        self._count = FileSystemEvent.COUNT
        self._root = root
        self._watchdog_event = watchdog

    def combine(self, other):
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
        FileSystemEvent.COUNT += 1
        self._count = FileSystemEvent.COUNT
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
        events = []
        for key, child in self._children.items():
            if isinstance(child, MoveMixin) and child.dest_path.startswith(self.dest_path):
                continue
            if isinstance(child, ChainedEvent):
                for evt in child._events:
                    if not isinstance(evt, MoveMixin):
                        events.append((key, evt))
            else:
                events.append((key, child))
        return OrderedDict(events)

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
            self._root.insert(events.FileModifiedEvent(event.dest_path))
            return event

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

        if isinstance(event, FileModifiedEvent):
            return ChainedEvent(self, event)

        raise NotImplementedError

### End File Events ###


class _EventConsolidator:
# class EventConsolidator:

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

        events = sum([
            event.watchdog_event if isinstance(event.watchdog_event, list) else [event.watchdog_event]
            for event in sorted(flatten(self, []), key=lambda x: x._count)
            if not isinstance(event, (FolderModifiedEvent, FileMovedDestination, FolderMovedDestination))
        ], [])

        # import ipdb; ipdb.set_trace()
        return events
        # return sorted(events, key=lambda x: x.src_path.count(os.path.sep), reverse=True)

        # groups = {}
        # for type, group in itertools.groupby(events, lambda x: x.event_type):
        #     groups[type] = list(group)

        # return sum([
        #     sorted(groups.get(type, []), key=lambda x: x.src_path.count(os.path.sep))
        #     for type in (
        #         EVENT_TYPE_DELETED,
        #         EVENT_TYPE_CREATED,
        #         EVENT_TYPE_MODIFIED,
        #         EVENT_TYPE_MOVED,
        #     )
        # ], [])

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



class Item:

    def __init__(self, is_folder, modified=False):
        self.modified = False
        self.is_folder = is_folder
        # self._path = path
        # self._event = event


class EventConsolidator:

    @property
    def events(self):
        i_pool = {v:k for k,v in self._pool.items()}
        i_final = {v: k for k,v in self._final.items()}
        i_initial = {v: k for k,v in self._initial.items()}

        moved = set()
        created = set(self._final.keys()) - set(self._initial.keys())
        deleted = set(self._initial.keys()) - set(self._final.keys())
        modified = set(i for i in self._pool.values() if i.modified and not i.is_folder)

        for key in set(created):
            src = i_initial.get(self._final[key])
            if src:
                created.remove(key)
                moved.add((src, key))

        for key in set(deleted):
            dest = i_final.get(self._initial[key])
            if dest:
                deleted.remove(key)
                moved.add((key, dest))

        sorter = lambda x: x.count(os.path.sep)

        evts = list(itertools.chain(
            (
                events.DirMovedEvent(src, dest)
                if self._final[dest].is_folder else
                events.FileMovedEvent(src, dest)
                for src, dest in sorted(moved, key=lambda x: x[0].count(os.path.sep), reverse=True)
            ),
            (
                events.DirDeletedEvent(x)
                if self._initial[x].is_folder else
                events.FileDeletedEvent(x)
                for x in sorted(deleted, key=sorter, reverse=True)
            ),
            (
                events.DirCreatedEvent(x)
                if self._final[x].is_folder else
                events.FileCreatedEvent(x)
                for x in sorted(created, key=sorter, reverse=True)
            ),
            (
                events.FileModifiedEvent(i_pool[x])
                for x in modified
                if x in i_final and not i_pool[x] in created
            ),
        ))

        mapped = set([
            (getattr(event, 'dest_path', event.src_path), event.event_type)
            # (event.src_path, event.event_type)
            for event in evts
            if event.is_directory
            and not event.event_type == EVENT_TYPE_CREATED
        ])

        def check(event):
            segments = getattr(event, 'dest_path', event.src_path).split(os.path.sep)
            for i in range(len(segments) - 1):
                if (os.path.sep.join(segments[:i + 1]), event.event_type) in mapped:
                    return False
            return True

        return list(sorted(filter(check, evts), key=lambda x: x.is_directory, reverse=True))

    def __init__(self):
        self._events = []
        self._pool = OrderedDict()
        self._final = OrderedDict()
        self._initial = OrderedDict()

    def clear(self):
        self._events = []
        self._pool.clear()
        self._final.clear()
        self._initial.clear()

    def push(self, event):
        self._events.append(event)

        self._push(event.src_path, event)
        if event.event_type == EVENT_TYPE_MOVED:
            self._push(event.dest_path, event, self._pool[event.src_path])

    def _push(self, path, event, item=None):
        created = path not in self._pool
        item = self._pool.setdefault(path, item or Item(event.is_directory))

        if event.event_type == EVENT_TYPE_MODIFIED:
            item.modified = True

        if event.event_type != EVENT_TYPE_DELETED and (event.event_type != EVENT_TYPE_MOVED or path == event.dest_path):
            self._final[path] = item
        else:
            self._final.pop(path, None)
            for key in list(self._final.keys()):
                if key.startswith(path):
                    self._final.pop(key)

        if created and event.event_type != EVENT_TYPE_CREATED and (event.event_type != EVENT_TYPE_MOVED or path == event.src_path):
            self._initial[path] = item
        elif not (event.event_type == EVENT_TYPE_MOVED and event.src_path == path):
            self._initial.pop(path, None)
            for key in list(self._initial.keys()):
                if key.startswith(path):
                    self._initial.pop(key)

    insert = push
