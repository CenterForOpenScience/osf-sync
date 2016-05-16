import logging
from pathlib import Path
import threading

from watchdog.events import EVENT_TYPE_CREATED, FileSystemEventHandler

from osfoffline import settings, utils
from osfoffline.exceptions import NodeNotFound
from osfoffline.sync.utils import EventConsolidator

logger = logging.getLogger(__name__)


def sha256_from_event(event):
    try:
        node = utils.extract_node(event.src_path)
    except NodeNotFound:
        db_file = None
    else:
        db_file = utils.local_to_db(event.src_path, node, check_is_folder=False)

    if not db_file:
        path = getattr(event, 'dest_path', None)
        if event.event_type == EVENT_TYPE_CREATED:
            path = event.src_path

        if not path:
            return None
        else:
            try:
                return utils.hash_file(Path(path))
            except (IsADirectoryError, PermissionError):
                return None
    else:
        return db_file.sha256


# class ConsolidatedEventHandler(PatternMatchingEventHandler):
class ConsolidatedEventHandler(FileSystemEventHandler):

    def __init__(self):
        # super().__init__(ignore_patterns=settings.IGNORED_PATTERNS)
        self._event_cache = EventConsolidator()
        self.timer = threading.Timer(settings.EVENT_DEBOUNCE, self.flush)
        self.timer.start()
        self.lock = threading.RLock()

    def dispatch(self, event):
        with self.lock:
            logger.debug('Watchdog event fired: {}'.format(event))
            self._event_cache.push(event)

            # try:
            #     # Stash the sha256, basename, and parts. This allows us to do consolidation
            #     # down the line.
            #     event.basename = os.path.basename(event.src_path)
            #     event.sha256 = sha256_from_event(event)
            #     event.parts = parts
            # except FileNotFoundError:
            #     return  # If the file is delete while attempting to SHA it, leave.

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
