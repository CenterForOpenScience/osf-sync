import collections
import logging
import sys
import textwrap

import npyscreen


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


class DecisionForm(npyscreen.ActionPopup):
    SHOW_ATT = 2
    SHOW_ATX = 10
    DEFAULT_LINES = 12
    DEFAULT_COLUMNS = 120

    def __init__(self, intervention, parentApp=None):
        self.intervention = intervention
        super().__init__(parentApp=parentApp)

    def create(self):
        self.center_on_display()
        # self.preserve_selected_widget = True
        mlw = self.add(wgmultiline.Pager,)
        text = [self.intervention.__class__.__name__ + ':']
        text.extend(textwrap.wrap(self.intervention.description, self.DEFAULT_COLUMNS - 10))
        mlw.values = text

    def generate_button(self, option):
        class OptionButton(wgbutton.MiniButtonPress):
            def whenPressed(self):
                self.parent.editing = False
                self.parent.value = option
        return OptionButton

    def create_control_buttons(self):
        offset = -2
        for i, option in enumerate(self.intervention.options):
            offset -= 3
            offset -= len(str(option))
            self._add_button(str(i), self.generate_button(option), str(option), -2, offset, None)


class NodeSyncForm(npyscreen.ActionPopup):
    SHOW_ATT = 2
    SHOW_ATX = 10
    DEFAULT_LINES = 8
    DEFAULT_COLUMNS = 60
    OK_BUTTON_TEXT = 'Login'
    CANCEL_BUTTON_BR_OFFSET = (2, 14)


class LoginForm(npyscreen.ActionPopup):
    SHOW_ATT = 2
    SHOW_ATX = 10
    DEFAULT_LINES = 8
    DEFAULT_COLUMNS = 60
    OK_BUTTON_TEXT = 'Login'
    CANCEL_BUTTON_BR_OFFSET = (2, 14)

    def create(self):
        self.center_on_display()

        self.name = 'Login'

        self.username = self.add(npyscreen.TitleText, name="Username:")
        self.password = self.add(npyscreen.TitlePassword, name="Password:", rely=4)

    def on_ok(self):
        try:
            user = AuthClient().login(username=self.username.value, password=self.password.value)
        except AuthError as ex:
            logger.exception(ex.message)
            npyscreen.notify_confirm(ex.message, 'Log in Failed')
        else:
            logger.info('Successfully logged in user: {}'.format(user))
            self.parentApp.background_handler.start()
            self.parentApp.setNextForm('MAIN')

    def on_cancel(self):
        self.parentApp.setNextForm(None)


class MainForm(npyscreen.Form):

    def create(self):
        self.queue_status = self.add(npyscreen.TitleText, name='Queue Status', max_height=3, value='0', editable=False, max_width=25)

        self.sync_now = self.add(npyscreen.ButtonPress, name='Sync Now', relx=-15, rely=2)
        self.sync_now.whenPressed = self._sync_now

        self.queue = self.add(npyscreen.BoxTitle, name='Queue', rely=4, max_height=10)
        self.queue.entry_widget.scroll_exit = True

        self.logs = self.add(npyscreen.BufferPager, name='Logs')

        self.add_event_hander('STDWRITEEVENT', self.ev_std_write_event_handler)
        self.add_event_hander('INTERVENTIONEVENT', self.ev_intervention_event_handler)
        self.add_event_hander('NOTIFICATIONEVENT', self.ev_notification_event_handler)

    def _sync_now(self):
        RemoteSyncWorker().sync_now()

    def ev_std_write_event_handler(self, event):
        msg = event.payload
        self.logs.buffer([msg])
        self.logs.display()

    def ev_intervention_event_handler(self, event):
        intervention = event.payload

        df = DecisionForm(intervention, parentApp=self)
        df.edit()

        logger.info('Got decision {} for {}'.format(df.value, intervention))
        intervention.set_result(df.value)

    def ev_notification_event_handler(self, event):
        notification = event.payload
        self.logs.buffer([notification])
        self.logs.display()

    def while_waiting(self):
        self.queue_status.value = '{}'.format(OperationWorker()._queue.qsize())
        self.queue_status.display()
        self.queue.values = list(OperationWorker()._queue.queue)
        self.queue.display()
        self.logs.display()


class App(npyscreen.StandardApp):

    def __init__(self, background_handler):
        super().__init__()
        self.background_handler = background_handler
        stdout_wrapper.on_write = self.on_std_write
        stderr_wrapper.on_write = self.on_std_write

        self.background_handler.set_intervention_cb(self.on_intervention)
        self.background_handler.set_notification_cb(self.on_notification)

    def onStart(self):
        self.keypress_timeout_default = 1

        self.main = self.addForm('MAIN', MainForm)
        self.login = self.addForm('LOGIN', LoginForm)

        self.user = None
        try:
            self.user = Session().query(models.User).one()
        except NoResultFound:
            pass
        else:
            try:
                AuthClient().populate_user_data(self.user)
            except AuthError:
                return self.setNextForm('LOGIN')

        self.background_handler.start()

    def on_std_write(self, msg):
        if not msg == '\n':
            self.event_queues['MAINQUEUE'].interal_queue.appendleft(npyscreen.Event("STDWRITEEVENT", msg))

    def on_intervention(self, intervention):
        self.event_queues['MAINQUEUE'].interal_queue.appendleft(npyscreen.Event("INTERVENTIONEVENT", intervention))

    def on_notification(self, notification):
        self.event_queues['MAINQUEUE'].interal_queue.appendleft(npyscreen.Event("NOTIFICATIONEVENT", notification))


if __name__ == '__main__':
    debug = 'debug' in sys.argv

    if not debug:
        sys.stdout = stdout_wrapper = StdWrapper(sys.stdout)
        sys.stderr = stderr_wrapper = StdWrapper(sys.stderr)

    from osfoffline import settings  # loads logging configuration

    from npyscreen import wgbutton
    from npyscreen import wgmultiline
    from sqlalchemy.orm.exc import NoResultFound

    from osfoffline.database import models
    from osfoffline.database import Session
    from osfoffline.exceptions import AuthError
    from osfoffline.utils.authentication import AuthClient
    from osfoffline.application.background import BackgroundHandler
    from osfoffline.tasks.queue import OperationWorker
    from osfoffline.sync.remote import RemoteSyncWorker

    background_handler = BackgroundHandler()

    try:
        if not debug:
            try:
                app = App(background_handler)
                app.run()
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                sys.stdout.write(stdout_wrapper.get_text())
                sys.stderr.write(stderr_wrapper.get_text())
        else:
            background_handler.start()
            RemoteSyncWorker().join()
    except KeyboardInterrupt:
        background_handler.stop()
