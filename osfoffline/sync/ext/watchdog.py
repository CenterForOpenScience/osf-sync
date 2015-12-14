from collections import OrderedDict
import os
import logging
import threading
from itertools import repeat

from watchdog.events import PatternMatchingEventHandler

from osfoffline import settings
from osfoffline.exceptions import NodeNotFound


logger = logging.getLogger(__name__)


class ConsolidatedEventHandler(PatternMatchingEventHandler):

    def __init__(self):
        super().__init__(ignore_patterns=settings.IGNORED_PATTERNS)
        self._event_cache = TreeDict()
        self.timer = threading.Timer(2, self.flush)
        self.timer.start()
        self.lock = threading.RLock()

    def dispatch(self, event):
        with self.lock:
            if event.is_directory and event.event_type == 'modified':
                return

            src_parts = event.src_path.split(os.path.sep)
            if not hasattr(event, 'dest_path'):
                dest_parts = repeat(None)
            else:
                dest_parts = event.dest_path.split(os.path.sep)

            self._event_cache[list(zip(repeat(event.event_type), src_parts, dest_parts))] = event

            self.timer.cancel()
            self.timer = threading.Timer(2, self.flush)
            self.timer.start()

    def flush(self):
        with self.lock:
            for e in self._event_cache.children():
                try:
                    super().dispatch(e)
                except (NodeNotFound, ) as ex:
                    logger.warning(ex)
                except Exception as ex:
                    logger.exception(ex)
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

    def children(self, keys=None):
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
