import threading
import time
import asyncio

class Concur(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.iterations = 0
        self.daemon = True  # OK for main to exit even if instance is still running
        self.paused = True  # start out paused
        self.state = threading.Condition()

    def run(self):
        self.resume() # unpause self
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop) # because background thread

        with self.state:
            if self.paused:
                self.state.wait() # block until notified

        # do stuff
        self.do_background_stuff()
        self.iterations += 1
        # if not self.loop.is_running():
        self.loop.run_forever()


    def do_background_stuff(self):

        print('just polled and observed in background')

        self.loop.call_soon(
            asyncio.async,
            self.check_osf()
        )

    @asyncio.coroutine
    def check_osf(self):
        while True:
            print('polled server')
            yield from asyncio.sleep(1)



    def resume(self):
        with self.state:
            self.paused = False
            self.state.notify()  # unblock self if waiting

    def pause(self):
        with self.state:
            self.paused = True  # make self block and wait

class KeepRunning(object):
    def __init__(self, seconds=60):
        self.run_time = seconds
        self.start_time = time.time()

    @property
    def condition(self):
        return time.time()-self.start_time < self.run_time

running = KeepRunning()
concur = Concur()
concur.start() # calls run() method

while running.condition:
  concur.resume()

  #let background stuff happen for 5 secs
  time.sleep(5)

  concur.pause()
  print('user has preferences open and is doing fun stuff for 10 sec')
  time.sleep(2)



print('concur.iterations == {}'.format(concur.iterations))  # show thread executed