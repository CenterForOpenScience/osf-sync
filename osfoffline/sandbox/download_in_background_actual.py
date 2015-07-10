__author__ = 'himanshu'
import asyncio
from threading import Thread

import aiohttp

from osfoffline.models import create_session


class Poll(Thread):
    def __init__(self, db_url, user):
        super().__init__()
        self._keep_running = True
        self.session = create_session(db_url)
        self.user = user
        # self._waiting_coros = Queue()
        # self._tasks = []
        self._loop = None                           # Loop must be initialized in child thread.
        # self.limit_simultaneous_processes = None    # Semaphore must be initialized after the loop is set.

    def stop(self):
        self._keep_running = False

    def run(self):
        self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.
        asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        # self.limit_simultaneous_processes = asyncio.Semaphore(2)
        self._loop.run_until_complete(self.get_remote_user())

    # def submit_coro(self, coro, callback=None):
    #     self._waiting_coros.put((coro, callback))

    @asyncio.coroutine
    def get_remote_user(self):
        url = 'https://staging2.osf.io:443/api/v2/users/?filter[fullname]={}'.format(self.user.fullname)
        response = yield from aiohttp.request('GET', url)
        content = yield from response.json()
        yield content['data'][0]



    # @asyncio.coroutine
    # def process_coros(self):
    #     while self._keep_running:
    #         try:
    #             while True:
    #                 coro, callback = self._waiting_coros.get_nowait()
    #                 task = asyncio.async(coro())
    #                 if callback:
    #                     task.add_done_callback(callback)
    #                 self._tasks.append(task)
    #         except Empty as e:
    #             pass
    #         yield from asyncio.sleep(3)     # sleep so the other tasks can run


poller = Poll()


# class Job(object):
#     def __init__(self, idx):
#         super().__init__()
#         self._idx = idx
#
#     def process(self):
#         background_worker.submit_coro(self._process, self._process_callback)
#
#     @asyncio.coroutine
#     def _process(self):
#         with (yield from background_worker.limit_simultaneous_processes):
#             print("received processing slot %d" % self._idx)
#             start = datetime.now()
#             yield from asyncio.sleep(2)
#             print("processing %d took %s" % (self._idx, str(datetime.now() - start)))
#
#     def _process_callback(self, future):
#         print("callback %d triggered" % self._idx)


def main():
    print("starting worker...")
    poller.start()  #started background thread. background_worker.run() must be called internally.


    command = None
    while command != "quit":
        import time
        time.sleep(1)
        print('1')
        # command = input("enter 'quit' to stop the program: \n")

    print("stopping...")
    poller.stop()
    poller.join()

if __name__=="__main__":
    main()