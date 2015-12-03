#!/usr/bin/env python
import asyncio
import logging
import os

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5.Qt import QIcon
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QSystemTrayIcon

from osfoffline.application.background import BackgroundWorker
from osfoffline.database import session
from osfoffline.database.models import User
from osfoffline.database.utils import save
from osfoffline.exceptions import AuthError
from osfoffline.utils.authentication import AuthClient
from osfoffline.utils.validators import validate_containing_folder
from osfoffline.views.preferences import Preferences
from osfoffline.views.login import LoginScreen
import osfoffline.alerts as AlertHandler
from osfoffline.application.menu import OSFOfflineMenu
import osfoffline.views.rsc.resources  # noqa


# RUN_PATH = "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"

logger = logging.getLogger(__name__)


class OSFApp(QSystemTrayIcon):
    login_signal = pyqtSignal()
    containing_folder_updated_signal = pyqtSignal()

    def __init__(self, application):
        super().__init__(QIcon(':/cos_logo_backup.png'), application)
        self.setContextMenu(OSFOfflineMenu(self))
        self.show()

        # worker
        self.background_worker = BackgroundWorker()

        # connect all signal-slot pairs
        self.setup_connections()

    def setup_connections(self):
        # [ (signal, slot) ]
        signal_slot_pairs = [

            # system tray
            (self.tray.open_osf_folder_action.triggered, self.tray.open_osf_folder),
            (self.tray.launch_osf_action.triggered, self.tray.start_osf),
            (self.tray.sync_now_action.triggered, self.sync_now),
            # (self.tray.currently_synching_action.triggered, self.controller.currently_synching),
            (self.tray.preferences_action.triggered, self.open_preferences),
            (self.tray.about_action.triggered, self.start_about_screen),

            (self.tray.quit_action.triggered, self.quit),
            (self.tray.tray_alert_signal, self.tray.update_currently_synching),

            # main events
            # (self.login_signal, self.start_screen.open_window),
            (self.start_tray_signal, self.tray.start),

            # preferences
            (self.preferences.ui.desktopNotifications.stateChanged, self.preferences.alerts_changed),
            (self.preferences.preferences_closed_signal, self.resume),
            (self.preferences.ui.accountLogOutButton.clicked, self.logout),
            # (self.preferences.containing_folder_updated_signal, self.preferences.update_containing_folder_text_box),

            # start screen
            # (self.start_screen.done_logging_in_signal, self.start),
            # (self.start_screen.quit_application_signal, self.quit),

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
        self.background_worker.start()

        return True

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

    def set_containing_folder_initial(self):
        return QFileDialog.getExistingDirectory(self, "Choose where to place OSF folder")

    def logout(self):
        # Will probably wipe out everything :shrug:
        session.query(User).delete()
        self.quit()
