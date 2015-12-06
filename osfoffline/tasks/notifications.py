import asyncio
import enum
import logging

from osfoffline.utils import Singleton


logger = logging.getLogger(__name__)


class Notification(metaclass=Singleton):
    thread_safe = True

    class Type(enum.Enum):

        INFO = 0,
        WARNING = 1,
        ERROR = 2

    class Event:

        def __init__(self, type, msg):
            self.type = type
            self.msg = msg

    def __init__(self):
        self.queue = asyncio.Queue()

    def set_callback(self, cb):
        self.cb = cb

    def info(self, msg):
        event = self.Event(self.Type.INFO, msg)
        logger.info('Notification: {}'.format(event))
        asyncio.get_event_loop().run_in_executor(None, self.cb, event)

    def warn(self, msg):
        event = self.Event(self.Type.WARNING, msg)
        logger.warn('Notification: {}'.format(event))
        asyncio.get_event_loop().run_in_executor(None, self.cb, event)

    def error(self, msg):
        event = self.Event(self.Type.ERROR, msg)
        logger.error('Notification: {}'.format(event))
        asyncio.get_event_loop().run_in_executor(None, self.cb, event)
