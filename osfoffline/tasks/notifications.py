import queue
import enum
import logging

from osfoffline.utils import Singleton


logger = logging.getLogger(__name__)


class Level(enum.IntEnum):
    """The severity of the notification event (determines display priority)"""
    INFO = 0
    WARNING = 1
    ERROR = 2


class Notification(metaclass=Singleton):

    class Event:
        def __init__(self, type, msg):
            """
            :param Level type: A severity ranking; must be member of the "Level" enumeration
            :param msg: Message text to be displayed to user
            """
            # TODO: Add additional fields describing event in more detail
            self.type = type
            self.msg = msg

        def __repr__(self):
            return '<{} ({}) {}>'.format(self.__class__.__name__, self.type.name, self.msg)

    def __init__(self):
        self.queue = queue.Queue()

    def set_callback(self, cb):
        self.cb = cb

    def info(self, msg):
        event = self.Event(Level.INFO, msg)
        logger.info('Notification: {}'.format(event))
        self.cb(event)

    def warn(self, msg):
        event = self.Event(Level.WARNING, msg)
        logger.warn('Notification: {}'.format(event))
        self.cb(event)

    def error(self, msg):
        event = self.Event(Level.ERROR, msg)
        logger.error('Notification: {}'.format(event))
        self.cb(event)


def group_events(event_list):
    """
    Group a list of events together based on level
    :param list event_list: A list of Event objects
    :return dict: A dictionary of the form {level_enum_value: [events]}
    """
    groups = {}
    for event in event_list:
        slot = groups.setdefault(event.type, [])
        slot.append(event)
    return groups
