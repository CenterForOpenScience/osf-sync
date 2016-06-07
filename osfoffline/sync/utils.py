import os
import sys
import logging
import itertools
from collections import deque
from collections import OrderedDict
from watchdog import events
from watchdog.events import (
    EVENT_TYPE_MOVED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MODIFIED,
)
from osfoffline.utils import is_ignored


logger = logging.getLogger(__name__)


class Item:

    def __init__(self, is_folder, modified=False):
        self.events = []
        self.modified = False
        self.is_folder = is_folder


class EventConsolidator:

    @property
    def events(self):
        if self._ignore:
            self._pool = OrderedDict([(k, v) for k, v in self._pool.items() if not is_ignored(k)])
            self._final = OrderedDict([(k, v) for k, v in self._final.items() if not is_ignored(k)])
            self._initial = OrderedDict([(k, v) for k, v in self._initial.items() if not is_ignored(k)])

        i_pool = {v: k for k, v in self._pool.items()}
        i_final = {v: k for k, v in self._final.items()}
        i_initial = {v: k for k, v in self._initial.items()}

        moved = set()
        created = set(self._final.keys()) - set(self._initial.keys())
        deleted = set(self._initial.keys()) - set(self._final.keys())
        modified = set(i for i in self._pool.values() if i.modified and not i.is_folder)

        # Probably don't need both loops here but better safe than sorry
        # If an item has been created and deleted it is actuall a move
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

        # Sort by place in the file hierarchy
        # Children come before parents
        # NOTE: Create events must be sorted THE OPPOSITE direction
        sorter = lambda x: x.count(os.path.sep)

        # Windows reports folder deletes are file deletes + modifies
        # If a child exists for any file assume it is a directory
        for delete in deleted:
            for other in deleted:
                if delete != other and other.startswith(delete):
                    self._initial[delete].is_folder = True
                    break

        evts = list(sorted(itertools.chain(
            (
                events.DirMovedEvent(src, dest)
                if self._final[dest].is_folder else
                events.FileMovedEvent(src, dest)
                for src, dest in sorted(moved, key=lambda x: x[0])
            ),
            (
                events.DirDeletedEvent(x)
                if self._initial[x].is_folder else
                events.FileDeletedEvent(x)
                for x in sorted(deleted)
            ),
            (
                events.DirCreatedEvent(x)
                if self._final[x].is_folder else
                events.FileCreatedEvent(x)
                for x in sorted(created)
            ),
            (
                events.FileModifiedEvent(i_pool[x])
                for x in modified
                if x in i_final and not i_pool[x] in created
            ),
        ), key=lambda x: x.src_path))

        mapped = set([
            (getattr(event, 'dest_path', event.src_path), event.event_type)
            for event in evts
            if event.is_directory
            and not event.event_type == EVENT_TYPE_CREATED
        ])

        # Do our best to dedup all found events.
        # If there is a matching event type at a parent path disregard the children
        def check(event):
            segments = getattr(event, 'dest_path', event.src_path).split(os.path.sep)
            for i in range(len(segments) - 1):
                if (os.path.sep.join(segments[:i + 1]), event.event_type) in mapped:
                    return not (event.event_type != EVENT_TYPE_MOVED or event.src_path.startswith(next(x[0] for x in moved if x[1] == os.path.sep.join(segments[:i + 1]))))
            return True

        return list(self.resolve_dependancies(filter(check, evts)))

    def __init__(self, ignore=True):
        self._events = []
        self._ignore = ignore
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

    def resolve_dependancies(self, events):
        # Implementation of a topological sort to resolve dependancies for
        # file system operations.
        # See Kahn's algorithm and https://en.wikipedia.org/wiki/Topological_sorting
        resolved = deque()
        by_path = {}
        references = OrderedDict()

        # Transform the list of events into a psuedo adjency list graph structure
        for event in events:
            if event.event_type == EVENT_TYPE_MOVED:
                segments = tuple(event.dest_path.strip(os.path.sep).split(os.path.sep))
            else:
                segments = tuple(event.src_path.strip(os.path.sep).split(os.path.sep))

            by_path.setdefault(segments, []).append(event)
            for i in range(1, len(segments) + 1):
                references.setdefault(segments[:i], set())
                for j in range(1, len(segments[i:]) + 1):
                    references[segments[:i]].add(segments[:i + j])

        # Resolve dependancies by finding all operations that have no dependancies
        # appending them to the resolved list and removing them as a dependancies from
        # all other operations. Continue until all dependancies have been resolved
        while references:
            for segments, refs in tuple(references.items()):
                if refs:
                    continue
                for i in range(len(segments)):
                    references[segments[:i + 1]].discard(segments)
                resolved.extendleft(by_path.pop(segments, []))
                del references[segments]

        return resolved

    def push(self, event):
        self._events.append(event)

        self._push(event.src_path, event)
        if event.event_type == EVENT_TYPE_MOVED:
            self._push(event.dest_path, event, self._pool[event.src_path])

    def _push(self, path, event, item=None):
        copy_found = False
        # For the case where windows decideds that moves should actually be creates and deletes
        # If a delete or create event with a hash is seen check the hash pool for an matching hash
        # If found ensure the found event is opposite of our current event and set item to it.
        if event.event_type in (events.EVENT_TYPE_CREATED, events.EVENT_TYPE_DELETED) and event.sha256:
            item = self._hash_pool.pop(event.sha256, None)
            if item and {event.event_type, item.events[0].event_type} != {events.EVENT_TYPE_CREATED, events.EVENT_TYPE_DELETED}:
                item = None
            elif item:
                copy_found = True
                item.modified = False
                self._pool[path] = item

        item = self._pool.setdefault(path, item or Item(event.is_directory))

        if sys.platform == 'win32' and event.event_type == EVENT_TYPE_MODIFIED and item.events and item.events[-1].event_type in (EVENT_TYPE_MOVED, EVENT_TYPE_CREATED):
            return  # Windows really likes emmiting modfied events. If a modified is prefaced by a MOVE or CREATE it should/can be ignored

        if event.sha256 and not copy_found:
            # If this is an unmatched event with a hash add it to the pool
            self._hash_pool.setdefault(event.sha256, item)

        item.events.append(event)

        if event.event_type == EVENT_TYPE_MODIFIED:
            item.modified = True

        if event.event_type != EVENT_TYPE_DELETED and (event.event_type != EVENT_TYPE_MOVED or path == event.dest_path):
            # If this event would result in the item in question existing in the final virtual state, add it.
            self._final[path] = item
        else:
            # Otherwise ensure that item and it's children, if any, are not in the final virutal state.
            self._final.pop(path, None)
            for key in list(self._final.keys()):
                if key.startswith(path):
                    self._final.pop(key)

        if event.event_type != EVENT_TYPE_CREATED and (event.event_type != EVENT_TYPE_MOVED or path == event.src_path):
            if (item.events[0].event_type == EVENT_TYPE_CREATED and not copy_found) or (item.events[0].event_type == EVENT_TYPE_MOVED and item.events[0].dest_path == path):
                return  # If this file was created by an event, don't create an initial place holder for it.
            # If this event indicates the item in question would have existed in the initial virtual state, add it.
            self._initial[path] = item
        else:
            # Otherwise ensure that item and it's children, if any, are not in the inital virtual state.
            self._initial.pop(path, None)
            for key in list(self._initial.keys()):
                if key.startswith(path):
                    self._initial.pop(key)
