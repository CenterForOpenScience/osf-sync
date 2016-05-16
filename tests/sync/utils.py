import threading
import time

from watchdog.observers import Observer

from osfoffline.sync.local import LocalSyncWorker
from osfoffline.sync.ext.watchdog import ConsolidatedEventHandler


class TestObserver(Observer):

    def __init__(self, *args, **kwargs):
        super(TestObserver, self).__init__(*args, **kwargs)
        self.ready = threading.Event()

    def on_thread_start(self):
        super(TestObserver, self).on_thread_start()
        # An arbitrary time... can't figure out why this fixes test failures. I do know
        # watchdog fails to pick up some events if this is missing.
        # TODO: find a non-arbitrary thing to wait on
        time.sleep(1)
        self.ready.set()

class TestSyncWorker(ConsolidatedEventHandler):

    def __init__(self, folder):
        super().__init__()

        self.observer = TestObserver()
        self.watch = self.observer.schedule(self, folder, recursive=True)

        self.start = self.observer.start
        self.stop = self.observer.stop
        self.join = self.observer.join

        self.flushed = threading.Event()
        self.done = threading.Event()

    def flush(self):
        with self.lock:
            self.flushed.set()
            self.done.wait()
            self._event_cache.clear()


class TestSyncObserver(LocalSyncWorker):

    def __init__(self, path, expected):
        super(LocalSyncWorker, self).__init__()
        self._events = []
        self.folder = path
        self.expected = expected
        self.observer = Observer()
        self.done = threading.Event()
        self.ignore = threading.Event()
        self.observer.schedule(self, self.folder, recursive=True)

    def put_event(self, event):
        self._events.append(event)
        if len(self._events) >= self.expected:
            self.done.set()
