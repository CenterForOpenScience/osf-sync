import asyncio
import logging

from asyncio.queues import Queue


from osfoffline.tasks import operations


logger = logging.getLogger(__name__)

try:
    asyncio.ensure_future
except AttributeError:
    asyncio.ensure_future = asyncio.async


class Queue(getattr(asyncio, 'JoinableQueue', asyncio.Queue)):
    """(Joinable)?Queue is broken in pretty much every version of python thus far
    This should fix it in >= 3.4.X and <= 3.5.0
    put/_put/__put_internal screws up _unfinished_tasks in a different way every version
    """

    def _put(self, item):
        self._queue.append(item)
        self._unfinished_tasks += 1
        self._finished.clear()

    def _Queue__put_internal(self, item):
        self._put(item)
        self._finished.clear()


class OperationsQueue(Queue):

    MAX_SIZE = 15

    # TODO Maybe fixme Could just ignore and give up on using MAX_SIZE
    # def __init__(self):
    #     super().__init__(maxsize=self.MAX_SIZE)

    @asyncio.coroutine
    def start(self):
        logger.info('start processing queue')
        while True:
            job = yield from self.get()
            logger.info('Running {}'.format(job))
            try:
                yield from job.run()
            finally:
                self.task_done()

    @asyncio.coroutine
    def put(self, event):
        if not isinstance(event, operations.BaseOperation):
            raise Exception('Invalid Event Type')
        yield from super().put(event)
