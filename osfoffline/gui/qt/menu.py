import logging
import os
import sys
import subprocess
import webbrowser

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMenu

from osfoffline import settings
from osfoffline.database import Session
from osfoffline.database.models import User
from osfoffline.gui.qt.preferences import Preferences
from osfoffline.utils.validators import validate_containing_folder


logger = logging.getLogger(__name__)


class OSFOfflineMenu(QMenu):

    push_status = pyqtSignal((str,))

    def __init__(self, parent):
        super().__init__()
        self.status = QAction('Up to Date', self)
        self.status.setDisabled(True)

        self.addAction(QAction('Open OSF Folder', self, triggered=self.open_folder))
        self.addAction(QAction('Launch OSF', self, triggered=self.open_osf))
        self.addSeparator()
        self.addAction(QAction('Sync Now', self, triggered=parent.sync_now))
        self.addAction(self.status)
        self.addSeparator()
        self.addAction(QAction('Settings', self, triggered=self.open_settings))
        self.addAction(QAction('About', self, triggered=self.open_about))
        self.addSeparator()
        self.addAction(QAction('Log Out', self, triggered=parent.logout))
        self.addAction(QAction('Quit', self, triggered=parent.quit))

        self.parent = parent
        self.preferences = Preferences()
        self.push_status.connect(self.update_status)

    def update_status(self, val):
        self.status.setText(str(val))

    def open_folder(self):
        user = Session().query(User).one()
        logger.debug("containing folder is :{}".format(user.folder))
        if validate_containing_folder(user.folder):
            if sys.platform == 'win32':
                os.startfile(user.folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', user.folder])
            else:
                try:
                    subprocess.Popen(['xdg-open', user.folder])
                except OSError:
                    pass

    def open_osf(self):
        webbrowser.open_new_tab(settings.OSF_URL)

    def open_settings(self):
        self.preferences.open_window(Preferences.GENERAL)

    def open_about(self):
        self.preferences.open_window(Preferences.ABOUT)
