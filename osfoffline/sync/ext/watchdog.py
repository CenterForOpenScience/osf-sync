from collections import OrderedDict
from itertools import repeat, chain
import logging
import os
import threading

from watchdog.events import PatternMatchingEventHandler

from osfoffline import settings
from osfoffline.exceptions import NodeNotFound


logger = logging.getLogger(__name__)


class ConsolidatedEventHandler(PatternMatchingEventHandler):

    def __init__(self):
        super().__init__(ignore_patterns=settings.IGNORED_PATTERNS)
        self._event_cache = TreeDict()
        self._create_cache = []
        self.timer = threading.Timer(5, self.flush)
        self.timer.start()
        self.lock = threading.RLock()

    def dispatch(self, event):
        with self.lock:
            src_parts = event.src_path.split(os.path.sep)
            if not hasattr(event, 'dest_path'):
                dest_parts = repeat(None)
            else:
                dest_parts = event.dest_path.split(os.path.sep)

            parts = list(zip(src_parts, dest_parts))

            # Windows represents folder deletes incorrectly as file deletes, and as
            # result we can't trust event.is_directory to check whether or not delete
            # events need to be consolidated
            consolidate = event.is_directory
            if event.event_type == 'deleted':
                consolidate = (parts in self._event_cache)

            if event.is_directory and event.event_type == 'modified':
                return

            try:
                if event.is_directory and event.event_type == 'created':
                    self._create_cache.extend(self._event_cache.children(keys=parts))

                if not consolidate and parts in self._event_cache and self._event_cache[parts].event_type == 'deleted':
                    # TODO: Deleting a folder with files still causes error
                    # Would technically be more correct to create a modified event but only event_type is checked, not the type
                    # Turn deletes followed by creates into updates IE saving in vim or replacing a file in finder
                    event.event_type = 'modified'
                self._event_cache[parts] = event
            except (TypeError, AttributeError):  # A parent event had already been processed
                if event.event_type == 'created':
                    self._create_cache.append(event)

            self.timer.cancel()
            self.timer = threading.Timer(2, self.flush)
            self.timer.start()

    def flush(self):
        with self.lock:
            for e in chain(self._event_cache.children(), sorted(self._create_cache, key=lambda x: x.src_path.count(os.path.sep))):
                try:
                    super().dispatch(e)
                except (NodeNotFound, ) as e:
                    logger.warning(e)
                except Exception as e:
                    logger.exception(e)
            self._create_cache = []
            self._event_cache = TreeDict()


def flatten(dict_obj, acc):
    for value in dict_obj.values():
        if isinstance(value, dict):
            flatten(value, acc)
        else:
            acc.append(value)
    return acc


class TreeDict:

    def __init__(self):
        self._inner = OrderedDict()

    def __setitem__(self, keys, value):
        inner = self._inner
        for key in keys[:-1]:
            inner = inner.setdefault(key, OrderedDict())
        inner[keys[-1]] = value

    def __getitem__(self, keys):
        if not isinstance(keys, (tuple, list)):
            keys = (keys,)
        inner = self._inner
        for key in keys:
            inner = inner[key]
        return inner

    def children(self, *, keys=None):
        try:
            sub_dict = self[keys] if keys is not None else self._inner
        except KeyError:
            return []
        return flatten(sub_dict, [])

    def __contains__(self, keys):
        try:
            self[keys]
        except KeyError:
            return False
        return True

    def __delitem__(self, keys):
        self[keys] = OrderedDict()
