import os
import sys
import time
import logging
import threading
from collections import OrderedDict
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler


class EventHandler(PatternMatchingEventHandler, LoggingEventHandler):

    def __init__(self):
        super().__init__(ignore_patterns=['*.DS_Store'])
        self._event_cache = OrderedDict()
        self.timer = threading.Timer(2, self.flush)
        self.timer.start()
        self.lock = threading.RLock()

    def dispatch(self, event):
        with self.lock:
            if event.is_directory and event.event_type == 'modified':
                return

            src_parent = event.src_path.split(os.path.sep)
            src_parent, src_name = src_parent[:-1], src_parent[-1]
            if not hasattr(event, 'dest_path'):
                dest_parent, dest_name = [None for _ in src_parent], None
            else:
                dest_parent = event.dest_path.split(os.path.sep)
                dest_parent, dest_name = dest_parent[:-1], dest_parent[-1]

            cache = self._event_cache
            for src_seg, dest_seg in zip(src_parent, dest_parent):
                if not isinstance(cache, dict):
                    break
                cache = cache.setdefault((event.event_type, src_seg, dest_seg), OrderedDict())
            else:
                if isinstance(cache, dict):
                    cache[(event.event_type, src_name, dest_name)] = event

            self.timer.cancel()
            self.timer = threading.Timer(2, self.flush)
            self.timer.start()

    def flush(self):
        with self.lock:
            for e in flatten(event_handler._event_cache, []):
                super().dispatch(e)
            event_handler._event_cache = OrderedDict()


def flatten(d, l):
    for x in d.values():
        if isinstance(x, dict):
            flatten(x, l)
        else:
            l.append(x)
    return l


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
