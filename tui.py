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
from osfoffline.tasks.queue import OperationsQueue, InterventionQueue

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

        self.operation_queue = OperationsQueue()
        self.operation_queue_task = asyncio.ensure_future(self.operation_queue.start())
        self.operation_queue_task.add_done_callback(self._handle_exception)

        self.intervention_queue = InterventionQueue()
        self.database_sync = DatabaseSync(self.operation_queue, self.intervention_queue, user)
        self.loop.run_until_complete(self.database_sync.check())

    def _handle_exception(self, future):
        logger.info('In handle exception')
        if future.exception():
            logger.info('Sync.handle_exception')
            # self.database_task.cancel()
            # self.queue_task.cancel()
            # raise future.exception()
            raise Exception('blah')

    def stop(self):
        if self.loop:
            self.loop.stop()


class DecisionForm(npyscreen.ActionPopup):

    class OptionButton(npyscreen.MiniButtonPress):
        def __init__(self, *args, **kwargs):
            super().__init__()
        def whenPressed(self):
            return self.parent.value = self.option

    # def create(self):
    #     self.queue_status = self.add(npyscreen.TitleText, name="Queue Status", max_height=3, value='0', editable=False)
    def create_control_buttons(self):
        super().create_control_buttons()
        for option in self.intervention.options:
            self._add_button(
                '{}_button'.format(option),
                ChoiceButton,
                str(option)
                10,
                10,
                None
            )

        self._add_button('ok_button',
                    self.__class__.OKBUTTON_TYPE,
                    self.__class__.OK_BUTTON_TEXT,
                    0 - self.__class__.OK_BUTTON_BR_OFFSET[0],
                    0 - self.__class__.OK_BUTTON_BR_OFFSET[1] - len(self.__class__.OK_BUTTON_TEXT),
                    None
                    )



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
        self.queue_status.value = '{}/{}'.format(self.parentApp.worker.operation_queue.qsize(), self.parentApp.worker.operation_queue.MAX_SIZE)
        self.queue_status.display()
        self.queue.values = list(self.parentApp.worker.operation_queue.queue._queue)
        self.queue.display()
        self.logs.display()


class App(npyscreen.StandardApp):

    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.loop = asyncio.get_event_loop()

    def onStart(self):
        self.keypress_timeout_default = 1

        self.addForm('MAIN', MainForm)

        self.worker.start()

    def while_waiting(self):
        try:
            intervention = self.worker.intervention_queue.get_nowait()
            # decision = npyscreen.notify_yes_no('testing', title="Message", form_color='STANDOUT', wrap=True, editw=0)
            decision = self._decision_form(intervention)
            asyncio.ensure_future(intervention.resolve(intervention.DEFAULT_DECISION), loop=self.worker.loop)
        except asyncio.QueueEmpty:
            pass

    def _decision_form(self):
        # def notify_yes_no(message, title="Message", form_color='STANDOUT', wrap=True, editw = 0,):
        message = _prepare_message(message)
        F   = DecisionForm(name=title, color=form_color)
        F.preserve_selected_widget = True
        mlw = F.add(wgmultiline.Pager,)
        mlw_width = mlw.width-1
        if wrap:
            message = _wrap_message_lines(message, mlw_width)
        mlw.values = message
        F.editw = editw
        F.edit()
        return F.value




if __name__ == '__main__':
    worker = BackgroundWorker()

    try:
        if not debug:
            try:
                app = App(worker)
                app.run()
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                sys.stdout.write(stdout_wrapper.get_text())
                sys.stderr.write(stderr_wrapper.get_text())
        else:
            worker.start()
            worker.join()
    except KeyboardInterrupt:
        worker.stop()
