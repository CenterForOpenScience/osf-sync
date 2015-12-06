import logging
import os

from queue import Queue

from PyQt5.Qt import QIcon
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QMutex
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QSystemTrayIcon

from sqlalchemy.orm.exc import NoResultFound

from osfoffline import settings
from osfoffline.application.background import BackgroundWorker
from osfoffline.database import session
from osfoffline.database.models import User
from osfoffline.database.utils import save
from osfoffline.gui.qt.login import LoginScreen
from osfoffline.gui.qt.menu import OSFOfflineMenu
from osfoffline.utils.validators import validate_containing_folder


logger = logging.getLogger(__name__)


class OSFOfflineQT(QSystemTrayIcon):

    def __init__(self, application):
        super().__init__(QIcon(':/tray_icon.png'), application)

        self.setContextMenu(OSFOfflineMenu(self))
        self.show()

        self.intervention_handler = SyncEventHandler()
        self.notification_handler = SyncEventHandler()

        # worker
        self.background_worker = BackgroundWorker()

        # [ (signal, slot) ]
        signal_slot_pairs = [
            # preferences
            # (self.preferences.ui.desktopNotifications.stateChanged, self.preferences.alerts_changed),
            # (self.preferences.preferences_closed_signal, self.resume),
            # (self.preferences.ui.accountLogOutButton.clicked, self.logout),
            (self.intervention_handler.notify_signal, self.on_intervention),
            (self.notification_handler.notify_signal, self.on_notification),
        ]
        for signal, slot in signal_slot_pairs:
            signal.connect(slot)

    def ensure_folder(self, user):
        containing_folder = os.path.dirname(user.folder or '')
        while not validate_containing_folder(containing_folder):
            logger.warning('Invalid containing folder: {}'.format(containing_folder))
            # AlertHandler.warn('Invalid containing folder. Please choose another.')
            containing_folder = os.path.abspath(QFileDialog.getExistingDirectory(caption='Choose where to place OSF folder'))

        user.folder = os.path.join(containing_folder, 'OSF')
        os.makedirs(user.folder, exist_ok=True)
        save(session, user)

    def start(self):
        logger.debug('Start in main called.')
        user = LoginScreen().get_user()
        if user is None:
            return False

        self.ensure_folder(user)

        logger.debug('starting background worker from main.start')
        self.background_worker = BackgroundWorker()
        self.background_worker.set_intervention_cb(self.intervention_handler.enqueue_signal.emit)
        self.background_worker.set_notification_cb(self.notification_handler.enqueue_signal.emit)
        self.background_worker.start()
        return True

    def on_intervention(self, intervention):
        message = QMessageBox()
        message.setWindowTitle('OSF Offline')
        message.setText(intervention.description)
        for option in intervention.options:
            message.addButton(str(option).split('.')[1], QMessageBox.YesRole)
        idx = message.exec()

        intervention.set_result(intervention.options[idx])

        self.intervention_handler.done()

    def on_notification(self, notification):
        # if (alert_icon is None) or (not show_alerts):
        #     return

        if not self.supportsMessages():
            return

        self.showMessage(
            'Title of The Message!!!',
            notification.msg,
            QSystemTrayIcon.NoIcon
        )

        self.notification_handler.done()

    def resume(self):
        logger.debug('resuming')
        if self.background_worker.is_alive():
            raise RuntimeError('Resume called without first calling pause')

        self.background_worker = BackgroundWorker()
        self.background_worker.start()

    def pause(self):
        logger.debug('pausing')
        if self.background_worker and self.background_worker.is_alive():
            self.background_worker.stop()

    def quit(self):
        try:
            if self.background_worker.is_alive():
                logger.info('Stopping background worker')
                self.background_worker.stop()

            try:
                user = session.query(User).one()
            except NoResultFound:
                pass
            else:
                logger.info('Saving user data')
                save(session, user)
            session.close()
        finally:
            logger.info('Quitting application')
            QApplication.instance().quit()

    def sync_now(self):
        self.background_worker.sync_now()

    def logout(self):
        # Will probably wipe out everything :shrug:
        session.query(User).delete()
        self.quit()


class SyncEventHandler(QThread):

    notify_signal = pyqtSignal(object)
    enqueue_signal = pyqtSignal(object)
    done_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.queue = Queue()
        self.mutex = QMutex()

        self.enqueue_signal.connect(self.queue.put)
        self.done_signal.connect(self.mutex.unlock)

        self.start()

    def done(self):
        self.done_signal.emit()

    def run(self):
        while True:
            event = self.queue.get()
            self.mutex.lock()
            self.notify_signal.emit(event)
