import sys
import logging
import collections

debug = 'debug' in sys.argv

logger = logging.getLogger(__name__)

class StdWrapper:

    MAXLEN = 1000

    def __init__(self, std):
        self.std = std
        self.text = collections.deque(maxlen=self.MAXLEN)

    def write(self, msg):
        self.text.append(msg)
        self.on_write(msg)

    def on_write(self, msg):
        pass

    def get_text(self):
        return ''.join(self.text)

    def fileno(self):
        return self.std.fileno()

if not debug:
    sys.stdout = stdout_wrapper = StdWrapper(sys.stdout)
    sys.stderr = stderr_wrapper = StdWrapper(sys.stderr)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')


import asyncio
import threading

import npyscreen

from osfoffline.database_manager.db import session
from osfoffline.database_manager import models
from osfoffline.sync.database import DatabaseSync
from osfoffline.tasks.queue import TaskQueue

try:
    asyncio.ensure_future
except AttributeError:
    asyncio.ensure_future = asyncio.async


class BackgroundWorker(threading.Thread):

    def __init__(self):
        super().__init__()
        self.loop = None

    def _ensure_event_loop(self):
        try:
            return asyncio.get_event_loop()
        except (AssertionError, RuntimeError):
            asyncio.set_event_loop(asyncio.new_event_loop())
        return asyncio.get_event_loop()

    def run(self):
        self.loop = self._ensure_event_loop()

        root_dir = '/Users/michael/Desktop/OSF'
        user = session.query(models.User).one()

        self.queue = TaskQueue()
        self.queue_task = asyncio.ensure_future(self.queue.start(), loop=self.loop)
        self.queue_task.add_done_callback(self._handle_exception)

        self.database_sync = DatabaseSync(self.queue, user)
        self.loop.run_until_complete(self.database_sync.check(intervention_cb=self._handle_intervention))

        self.loop.run_until_complete(self.queue.join())

    @asyncio.coroutine
    def _handle_intervention(self, intervention):
        return (yield from self.loop.run_in_executor(None, self.handle_intervention, intervention))

    def handle_intervention(self, intervention):
        raise NotImplementedError

    def _handle_exception(self, future):
        if future.exception():
            logger.info('Sync.handle_exception')
            # self.database_task.cancel()
            # self.queue_task.cancel()
            # raise future.exception()
            raise Exception('blah')

    def stop(self):
        if self.loop:
            self.loop.stop()


class MainForm(npyscreen.Form):

    def create(self):
        self.queue_status = self.add(npyscreen.TitleText, name="Queue Status", max_height=3, value='0', editable=False)

        self.queue = self.add(npyscreen.BoxTitle, name="Queue", rely=4, max_height=10)
        self.queue.entry_widget.scroll_exit = True

        self.logs = self.add(npyscreen.BufferPager, name="Logs")

        stdout_wrapper.on_write = self._on_std_write
        stderr_wrapper.on_write = self._on_std_write

    def _on_std_write(self, msg):
        if not msg == '\n':
            self.logs.buffer([msg])

    def while_waiting(self):
        self.queue_status.value = '{}/{}'.format(self.parentApp.thread.queue.qsize(), self.parentApp.thread.queue.MAX_SIZE)
        self.queue_status.display()
        self.queue.values = list(self.parentApp.thread.queue.queue._queue)
        self.queue.display()
        self.logs.display()


class App(npyscreen.StandardApp):

    def __init__(self, thread):
        super().__init__()
        self.thread = thread
        self.intervention_lock = threading.Lock()
        self.intervention_event = threading.Event()
        self.intervention_decision = None

    def onStart(self):
        self.keypress_timeout_default = 1

        self.addForm('MAIN', MainForm)

        self.thread.handle_intervention = self._handle_intervention
        self.thread.start()

        self.add_event_hander("INTERVENTION_EVENT", self.intervention_event_handler)

    def intervention_event_handler(self, event):
        intervention = event.payload
        decision = npyscreen.notify_yes_no('testing', title="Message", form_color='STANDOUT', wrap=True, editw=0)
        if decision:
            self.intervention_decision = intervention.DEFAULT_DECISION
        else:
            self.intervention_decision = intervention.DEFAULT_DECISION
        self.intervention_event.set()

    def _handle_intervention(self, intervention):
        with self.intervention_lock:
            # TODO: need a better way to signal into the npyscreen main loop, for now this works...
            self.intervention_event.clear()
            self.queue_event(npyscreen.Event("INTERVENTION_EVENT", intervention))
            self.intervention_event.wait()
            return self.intervention_decision


if __name__ == '__main__':
    thread = BackgroundWorker()

    try:
        if not debug:
            try:
                app = App(thread)
                app.run()
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                sys.stdout.write(stdout_wrapper.get_text())
                sys.stderr.write(stderr_wrapper.get_text())
        else:
            thread.start()
            thread.join()
    except KeyboardInterrupt:
        thread.stop()
