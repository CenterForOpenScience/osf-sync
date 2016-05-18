import os
import sys
import logging
import itertools
from collections import OrderedDict
from watchdog import events
from watchdog.events import (
    EVENT_TYPE_MOVED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MODIFIED,
)

from osfoffline import utils

logger = logging.getLogger(__name__)


class Item:

    def __init__(self, is_folder, modified=False):
        self.events = []
        self.modified = False
        self.is_folder = is_folder


class EventConsolidator:

    @property
    def events(self):
        i_pool = {v: k for k, v in self._pool.items()}
        i_final = {v: k for k, v in self._final.items()}
        i_initial = {v: k for k, v in self._initial.items()}

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
                for x in sorted(created, key=sorter)
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

        return list(filter(check, evts))

    def __init__(self):
        self._events = []
        self._pool = OrderedDict()
        self._final = OrderedDict()
        self._initial = OrderedDict()
        self._hash_pool = OrderedDict()

    def clear(self):
        self._events = []
        self._pool.clear()
        self._final.clear()
        self._initial.clear()
        self._hash_pool.clear()

    def push(self, event):
        self._events.append(event)

        self._push(event.src_path, event)
        if event.event_type == EVENT_TYPE_MOVED:
            self._push(event.dest_path, event, self._pool[event.src_path])

    def _push(self, path, event, item=None):
        copy_found = False
        if event.event_type in (events.EVENT_TYPE_CREATED, events.EVENT_TYPE_DELETED) and event.sha256:
            item = self._hash_pool.pop(event.sha256, None)
            if item and {event.event_type, item.events[0].event_type} != {events.EVENT_TYPE_CREATED, events.EVENT_TYPE_DELETED}:
                item = None
            elif item:
                copy_found = True
                item.modified = False
                self._pool[path] = item

        item = self._pool.setdefault(path, item or Item(event.is_directory))

        if event.sha256 and not copy_found:
            self._hash_pool.setdefault(event.sha256, item)

        item.events.append(event)

        if event.event_type == EVENT_TYPE_MODIFIED and not (sys.platform == 'win32' and len(item.events) > 1 and item.events[-2].event_type == EVENT_TYPE_MOVED):
            # Windows reports moved files as modified even if they are not, ignore these. Any changes will be picked up by the remote sync
            item.modified = True

        if event.event_type != EVENT_TYPE_DELETED and (event.event_type != EVENT_TYPE_MOVED or path == event.dest_path):
            self._final[path] = item
        else:
            self._final.pop(path, None)
            for key in list(self._final.keys()):
                if key.startswith(path):
                    self._final.pop(key)

        if event.event_type != EVENT_TYPE_CREATED and (event.event_type != EVENT_TYPE_MOVED or path == event.src_path):
            if (item.events[0].event_type == EVENT_TYPE_CREATED and not copy_found) or (item.events[0].event_type == EVENT_TYPE_MOVED and item.events[0].dest_path == path):
                return  # If this file was created by an event dont create an initial place holder for it.
            self._initial[path] = item
        else:
            self._initial.pop(path, None)
            for key in list(self._initial.keys()):
                if key.startswith(path):
                    self._initial.pop(key)
