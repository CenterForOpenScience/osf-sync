import asyncio
import datetime
from threading import Thread

class Poll(Thread):
    def __init__(self, db_url, user_osf_id):
        super().__init__()
        self._keep_running = True
        self._loop = None

    def stop(self):
        self._keep_running = False



    def run(self):

        self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.
        self.RECHECK_TIME = 5
        self._loop.call_soon(self.watchdog_events, self.RECHECK_TIME, self._loop)
        asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        # asyncio.async(self.background_tasks())
        self._loop.run_forever()
        # self._loop.run_until_complete(self.background_tasks())


    @asyncio.coroutine
    def background_tasks(self):
        while self._keep_running:
            asyncio.async(self.poll_api(1,1))
            asyncio.async(self.watchdog_events())

            yield from asyncio.sleep(5)

    @asyncio.coroutine
    def poll_api(self,x, y):
        print("polling api {}".format(x+y))
        yield from asyncio.sleep(0.1)


    # @asyncio.coroutine
    # def print_sum(self,x, y):
    #     result = yield from self.compute(x, y)
    #     print("%s + %s = %s" % (x, y, result))

    @asyncio.coroutine
    def watchdog_events(self):
        print("watching events via watchdog")
        yield from asyncio.sleep(1.0)



poll = Poll('as','as')
poll.start()
name= ''
while name !='quit':
    name = input('enter quit to quit')
poll.stop()
poll.join()

