from pathlib import Path
import threading

from watchdog.observers import Observer

from osfoffline.sync.ext.watchdog import ConsolidatedEventHandler
from osfoffline.utils import Singleton

class TestSyncWorker(ConsolidatedEventHandler, metaclass=Singleton):

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

        self.observer = Observer()
        self.observer.schedule(self, self.folder, recursive=True)

        self.start = self.observer.start
        self.stop = self.observer.stop()
        self.join = self.observer.join()

        self._last_event = None
        self._events = ('moved', 'created', 'deleted', 'modified')
        def handler(name, cls, event):
            self._clear_events()
            self._last_event = event
            getattr(self, 'on_{0}'.format(name)).set()

        for event in self._events:
            setattr(self, '_on_{}'.format(event), threading.Event())
            event_handler = functools.partial(handler, event)
            event_handler.__name__ = 'on_{}'.format(event)
            setattr(self, 'on_{}'.format(event), event_handler)

    def _clear_events(self):
        for event in self._events:
            getattr(self, '_on_{}'.format(event)).clear()

    def put_event(self, event):
        pass
