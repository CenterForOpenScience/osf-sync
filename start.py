#!/usr/bin/env python
import logging
import requests
import signal
import sys
from distutils.version import StrictVersion

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QSystemTrayIcon

from osfoffline.database import drop_db
from osfoffline.gui.qt import OSFOfflineQT
from osfoffline.utils.log import start_logging
from osfoffline.utils.singleton import SingleInstance
from osfoffline.tasks.notifications import Notification
from osfoffline import settings

from updater4pyi import upd_source, upd_core
from updater4pyi.upd_iface_pyqt4 import UpdatePyQt4Interface
from updater4pyi.upd_defs import Updater4PyiError


if settings.DEBUG:
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def running_warning(message):
    warn_app = QApplication(sys.argv)
    QMessageBox.information(None, 'Systray', message)
    warn_app.quit()


def start():
    start_logging()
    # will end application if an instance is already running
    SingleInstance(callback=running_warning('OSF-Offline is already running. Check out the system tray.'))

    # Check for updates first and give user a way to get new version
    try:
        swu_source = upd_source.UpdateGithubReleasesSource(settings.REPO)
        swu_updater = upd_core.Updater(current_version=settings.VERSION,
                                       update_source=swu_source)
        swu_interface = UpdatePyQt4Interface(updater=swu_updater,
                                             progname=settings.NAME,
                                             ask_before_checking=True,
                                             parent=QApplication.instance())
    except Updater4PyiError as e:
        logger = logging.getLogger(__name__)
        logger.exception(e.updater_msg)
        if 'Connection Error' in e.updater_msg:
            Notification().error('Cannot check for updates because you have no Internet connection.')

    min_version = None
    # Then, if the current version is too old, close the program
    try:
        r = requests.get(settings.MIN_VERSION_URL)
        min_version = r.json()['min-version']
    except requests.exceptions.ConnectionError:
        Notification().error('Check for minimun verion requirements for OSF-Offline failed '
                        'becasue you have no Internet connection')

    if min_version:
        if StrictVersion(settings.VERSION) < StrictVersion(min_version):
            # User error message
            running_warning('You must update to a newer version. You are currently using version {}. '
                            'The minimum required version is {}.'.format(settings.VERSION, min_version))
            sys.exit(1)

    # Start logging all events
    if '--drop' in sys.argv:
        drop_db()

    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, 'Systray', 'Could not detect a system tray on this system')
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    if not OSFOfflineQT(app).start():
        return sys.exit(1)
    return sys.exit(app.exec_())


if __name__ == "__main__":
    start()
