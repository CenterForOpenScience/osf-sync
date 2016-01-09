import threading

from watchdog.observers import Observer
from osfoffline.sync.ext.watchdog import (
    ConsolidatedEventHandler,
    TreeDict
)

class TestSyncWorker(ConsolidatedEventHandler):

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

        self.observer = Observer()
        self.observer.schedule(self, self.folder, recursive=True)

        self.start = self.observer.start
        self.stop = self.observer.stop
        self.join = self.observer.join

        self.flushed = threading.Event()
        self.done = threading.Event()

    def flush(self):
        self.flushed.set()
        self.done.wait()
        self._create_cache = []
        self._event_cache = TreeDict()
