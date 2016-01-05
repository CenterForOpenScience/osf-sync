import logging
import queue
import threading

from osfoffline import settings
from osfoffline.exceptions import NodeNotFound
from osfoffline.tasks.notifications import Notification
from osfoffline.utils import Singleton


logger = logging.getLogger(__name__)


class OperationWorker(threading.Thread, metaclass=Singleton):

    def __init__(self):
        super().__init__()
        self._queue = queue.Queue()
        self.__stop = threading.Event()

    def start(self, *args, **kwargs):
        logger.debug('Starting OperationWorker')
        super().start(*args, **kwargs)

    def run(self):
        logger.info('Start processing queue')
        while not self.__stop.is_set():
            job = self._queue.get()
            if job is None:
                self._queue.task_done()
                continue
            logger.info('Starting {}'.format(job))
            try:
                job.run(dry=settings.DRY)
            except (NodeNotFound, ) as e:
                logger.warning(e)
            except Exception as e:
                logger.exception(e)
                # TODO: How can we get filename from a given job, to display appropriate notification to the user?
                Notification().error('Error while updating')
            else:
                logger.info('Job successfully completed')
            finally:
                self._queue.task_done()
        logger.debug('OperationWorker stopped')

    def stop(self):
        logger.debug('Stopping OperationWorker')
        self.__stop.set()
        self._queue.put(None)
        self.join_queue()

    def put(self, operation):
        self._queue.put(operation)

    def join_queue(self):
        return self._queue.join()
