#!/usr/bin/env python
import logging
from json import JSONDecodeError

import requests
import signal
import sys
from distutils.version import StrictVersion

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QSystemTrayIcon

from osfsync.database import drop_db
from osfsync.gui.qt import OSFSyncQT
from osfsync.utils.log import start_logging
from osfsync.utils.singleton import SingleInstance
from osfsync.application.background import BackgroundHandler
from osfsync import settings

logger = logging.getLogger(__name__)


def exit_gracefully(*args):
    try:
        BackgroundHandler().stop()
    finally:
        sys.exit(1)


signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, exit_gracefully)


def running_warning(message=None, critical=False):
    if not message:
        message = 'OSF-Sync is already running. Check out the system tray.'
    warn_app = QApplication(sys.argv)
    if critical:
        QMessageBox.critical(None, 'Systray', message)
    else:
        QMessageBox.information(None, 'Systray', message)
    warn_app.quit()


def start():
    start_logging()

    # will end application if an instance is already running
    singleton = SingleInstance(callback=running_warning)

    min_version = None
    # Then, if the current version is too old, close the program
    if settings.MIN_VERSION_URL:
        try:
            r = requests.get(settings.MIN_VERSION_URL, timeout=settings.READ_TIMEOUT)
        except requests.exceptions.ConnectionError:
            logger.warning('Check for minimum version requirements for OSF-Sync failed '
                           'because you have no Internet connection')
        else:
            try:
                min_version = r.json()['min-version']
            except (KeyError, JSONDecodeError,) as e:
                logger.exception(e)

    if min_version:
        if StrictVersion(settings.VERSION) < StrictVersion(min_version):
            # User error message
            running_warning(message='You must update to a newer version. '
                                    'You can find newest version at {}'
                            .format(settings.PROJECT_ON_OSF),
                            critical=True)
            sys.exit(1)

    # Start logging all events
    if '--drop' in sys.argv:
        drop_db()

    app = QApplication(sys.argv)

    # connect QT to handle system shutdown signal from os correctly
    app.aboutToQuit.connect(exit_gracefully)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, 'Systray', 'Could not detect a system tray on this system')
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    if not OSFSyncQT(app).start():
        return sys.exit(1)
    return sys.exit(app.exec_())


if __name__ == "__main__":
    start()
