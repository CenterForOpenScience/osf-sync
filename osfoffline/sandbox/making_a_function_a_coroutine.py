__author__ = 'himanshu'
import asyncio

EVENT_TYPE_MOVED = 'moved'
EVENT_TYPE_DELETED = 'deleted'
EVENT_TYPE_CREATED = 'created'
EVENT_TYPE_MODIFIED = 'modified'

class OSFEventHandler(object):
    def __init__(self):
        self._loop = asyncio.new_event_loop()

    def start(self):
        self._loop.run_forever()

    @asyncio.coroutine
    def on_modified(self):
        print('on modified')
    @asyncio.coroutine
    def on_moved(self):
        print('on_moved')
    @asyncio.coroutine
    def on_created(self):
        print('on_created')
    @asyncio.coroutine
    def on_deleted(self):
        print('on_deleted')

    def dispatch(self, event):
        _method_map = {
            EVENT_TYPE_MODIFIED: self.on_modified,
            EVENT_TYPE_MOVED: self.on_moved,
            EVENT_TYPE_CREATED: self.on_created,
            EVENT_TYPE_DELETED: self.on_deleted,
        }

        handler = _method_map[event.event_type]

        self._loop.call_soon(
            asyncio.async,
            handler(event)
        )

if __name__=="__main__":
    osf = OSFEventHandler()
    while True:
        event = input('event:')
        osf.dispatch(event)
    osf.start()


