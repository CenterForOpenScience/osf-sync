import logging
import os
import sys
import threading
from queue import Empty, Queue

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QMutex
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QSystemTrayIcon

from sqlalchemy.orm.exc import NoResultFound

from osfoffline.application.background import BackgroundHandler
from osfoffline.client.osf import OSFClient
from osfoffline.database import Session
from osfoffline.database import drop_db
from osfoffline.database.models import User
from osfoffline.gui.qt.login import LoginScreen
from osfoffline.gui.qt.menu import OSFOfflineMenu
from osfoffline.utils.log import remove_user_from_sentry_logs
from osfoffline import settings
from osfoffline.tasks.notifications import group_events, Level
from osfoffline.utils.validators import validate_containing_folder

logger = logging.getLogger(__name__)

ON_WINDOWS = sys.platform == 'win32'
ON_MAC = sys.platform == 'darwin'

class QResizableMessageBox(QMessageBox):
    QWIDGETSIZE_MAX = 16777215

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMouseTracking(True)
        self.setSizeGripEnabled(True)

    def event(self, e):
        if e.type() in (QEvent.MouseMove, QEvent.MouseButtonPress):
            self.setMaximumSize(self.QWIDGETSIZE_MAX, self.QWIDGETSIZE_MAX)

            details_box = self.findChild(QTextEdit)
            if details_box is not None:
                details_box.setFixedSize(details_box.sizeHint())
        return QMessageBox.event(self, e)


class OSFOfflineQT(QSystemTrayIcon):

    def __init__(self, application):
        if ON_WINDOWS:
            super().__init__(QIcon(':/tray_icon_win.png'), application)
        else:
            super().__init__(QIcon(':/tray_icon_mac.png'), application)

        self._context_menu = OSFOfflineMenu(self)
        self.setContextMenu(self._context_menu)
        self.show()

        self.intervention_handler = SyncEventHandler()
        self.notification_handler = SyncEventHandler()

        # [ (signal, slot) ]
        signal_slot_pairs = [
            # preferences
            # (self.preferences.ui.desktopNotifications.stateChanged, self.preferences.alerts_changed),
            # (self.preferences.preferences_closed_signal, self.resume),
            (self._context_menu.preferences.accountLogOutButton.clicked, self.logout),
            (self.intervention_handler.notify_signal, self.on_intervention),
            (self.notification_handler.notify_signal, self.on_notification),
        ]
        for signal, slot in signal_slot_pairs:
            signal.connect(slot)

    def ensure_folder(self, user):
        containing_folder = os.path.dirname(user.folder or '')
        while not validate_containing_folder(containing_folder):
            logger.warning('Invalid containing folder: "{}"'.format(containing_folder))
            res = QFileDialog.getExistingDirectory(caption='Choose where to place OSF folder')
            if not res:
                # Do not accept an empty string (dialog box dismissed without selection)
                # FIXME: This fixes overt errors, but user gets folder picker endlessly until they select a folder
                continue
            else:
                containing_folder = os.path.abspath(res)

        with Session() as session:
            user.folder = os.path.join(containing_folder, 'OSF')
            os.makedirs(user.folder, exist_ok=True)
            session.add(user)
            session.commit()

    def start(self):
        logger.debug('Start in main called.')
        self.hide()
        user = LoginScreen().get_user()
        if user is None:
            return False

        self.ensure_folder(user)
        self.show()

        logger.debug('starting background handler from main.start')
        BackgroundHandler().set_intervention_cb(self.intervention_handler.enqueue_signal.emit)
        BackgroundHandler().set_notification_cb(self.notification_handler.enqueue_signal.emit)
        BackgroundHandler().start()

        if user.first_boot:
            self._context_menu.preferences.on_first_boot()
            self._context_menu.open_settings()

        return True

    def on_intervention(self, intervention):
        message = QResizableMessageBox()
        message.setWindowTitle('OSF Offline')
        message.setIcon(QMessageBox.Question)
        message.setText(intervention.title)
        message.setInformativeText(intervention.description)
        for option in intervention.options:
            option_language = str(option).split('.')[1]
            message.addButton(" ".join(option_language.split('_')), QMessageBox.YesRole)
        idx = message.exec()

        intervention.set_result(intervention.options[idx])

        self.intervention_handler.done()

    def on_notification(self, notification):
        """
        Display user-facing event notifications.

        :param notification: An individual notification event
        :return:
        """
        if not self.supportsMessages():
            return

        # Wait for more notifications, then grab all events and display
        t = threading.Timer(settings.ALERT_DURATION * 2, self._consolidate_notifications, args=[notification])
        t.start()

    # def resume(self):
    #     logger.debug('resuming')
    #     if self.background_handler.is_alive():
    #         raise RuntimeError('Resume called without first calling pause')

    #     self.background_handler = BackgroundHandler()
    #     self.background_handler.start()

    # def pause(self):
    #     logger.debug('pausing')
    #     if self.background_handler and self.background_handler.is_alive():
    #         self.background_handler.stop()

    def _consolidate_notifications(self, first_notification):
        """
        Consolidates notifications and groups them together. Releases a burst of all notifications that occur in
        a given window of time after the first message is received.
        Error messages are always displayed individually.

        :param first_notification: The first notification that triggered the consolidation cycle
        :return:
        """
        # Grab all available events, including the one that kicked off this consolidation cycle
        available_notifications = [first_notification]
        while True:
            try:
                event = self.notification_handler.queue.get_nowait()
            except Empty:
                break
            else:
                available_notifications.append(event)

        # Display notifications
        if len(available_notifications) == 1:
            # If there's only one message, show it regardless of level
            self._show_notifications(available_notifications)
        else:
            consolidated = group_events(available_notifications)
            for level, notification_list in consolidated.items():
                # Group info notifications, but display errors and warnings individually
                if level > Level.INFO:
                    self._show_notifications(notification_list)
                else:
                    self.showMessage(
                        'Updated multiple',
                        'Updated {} files and folders'.format(len(notification_list)),
                        QSystemTrayIcon.NoIcon,
                        msecs=settings.ALERT_DURATION / 1000.
                    )

        self.notification_handler.done()

    def _show_notifications(self, notifications_list):
        """Show a message bubble for each notification in the list provided"""
        for n in notifications_list:
            self.showMessage(
                'Synchronizing...',
                n.msg,
                QSystemTrayIcon.NoIcon,
                msecs=settings.ALERT_DURATION / 1000.
            )

    def quit(self):
        BackgroundHandler().stop()
        with Session() as session:
            try:
                user = session.query(User).one()
            except NoResultFound:
                pass
            else:
                logger.debug('Saving user data')
                session.add(user)
                session.commit()
            session.close()

        logger.info('Quitting application')
        QApplication.instance().quit()

    def sync_now(self):
        BackgroundHandler().sync_now()

    def logout(self):
        BackgroundHandler().stop()
        OSFClient().stop()
        # Will probably wipe out everything :shrug:
        drop_db()
        # Clear any user-specific context data that would be sent to Sentry
        remove_user_from_sentry_logs()

        # if the preferences window is active, close it.
        if self._context_menu.preferences.isVisible():
            self._context_menu.preferences.close()

        with Session() as session:
            session.close()

        logger.info('Restart the application.')
        self.start()


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
            self.mutex.lock()
            event = self.queue.get()
            self.notify_signal.emit(event)
