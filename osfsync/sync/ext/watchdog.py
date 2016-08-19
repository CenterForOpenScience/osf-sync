import sys
import logging
from pathlib import Path
import threading

from watchdog.events import EVENT_TYPE_DELETED, FileSystemEventHandler

from osfsync import settings, utils
from osfsync.exceptions import NodeNotFound
from osfsync.sync.utils import EventConsolidator

logger = logging.getLogger(__name__)


if sys.platform == 'win32':
    from watchdog.observers import winapi
    # Dont emit file modify events when a file's attributes are changed
    winapi.WATCHDOG_FILE_NOTIFY_FLAGS ^= winapi.FILE_NOTIFY_CHANGE_SECURITY
    winapi.WATCHDOG_FILE_NOTIFY_FLAGS ^= winapi.FILE_NOTIFY_CHANGE_ATTRIBUTES
    winapi.WATCHDOG_FILE_NOTIFY_FLAGS ^= winapi.FILE_NOTIFY_CHANGE_LAST_ACCESS


def sha256_from_event(event):
    if event.is_directory:
        return None

    try:
        node = utils.extract_node(event.src_path)
        db_file = utils.local_to_db(event.src_path, node, check_is_folder=False)
        if db_file:
            return db_file.sha256
    except NodeNotFound:
        pass

    if event.event_type == EVENT_TYPE_DELETED:
        return None

    try:
        return utils.hash_file(Path(getattr(event, 'dest_path', event.src_path)))
    except (IsADirectoryError, PermissionError):
        return None


class ConsolidatedEventHandler(FileSystemEventHandler):

    def __init__(self):
        self._event_cache = EventConsolidator()
        self.timer = threading.Timer(settings.EVENT_DEBOUNCE, self.flush)
        self.timer.start()
        self.lock = threading.RLock()

    def dispatch(self, event):
        with self.lock:
            logger.debug('Watchdog event fired: {}'.format(event))

            # Stash the sha256, basename, and parts. This allows us to do consolidation
            # down the line.
            try:
                event.sha256 = sha256_from_event(event)
            except FileNotFoundError:
                event.sha256 = None
                logger.warning('Could not open file to hash {}'.format(event))

            self._event_cache.push(event)

            self.timer.cancel()
            self.timer = threading.Timer(settings.EVENT_DEBOUNCE, self.flush)
            self.timer.start()

    def flush(self):
        with self.lock:
            # Create events after all other types, and parent folder creation events happen before child files
            logger.debug('Flushing event cache; Emitting {} events'.format(len(self._event_cache.events)))
            for event in self._event_cache.events:
                logger.info('Emitting event: {}'.format(event))
                try:
                    super().dispatch(event)
                except (NodeNotFound,) as e:
                    logger.warning(e)
                except Exception:
                    logger.exception('Failure while dispatching watchdog event: {}'.format(event))

            self._event_cache.clear()
