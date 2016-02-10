#!/usr/bin/env python
import logging
import requests
import signal
import sys
from distutils.version import StrictVersion

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QSystemTrayIcon

from osfoffline.database import drop_db
from osfoffline.gui.qt import OSFOfflineQT
from osfoffline.utils.log import start_logging
from osfoffline.utils.singleton import SingleInstance
from osfoffline.application.background import BackgroundHandler
from osfoffline import settings

logger = logging.getLogger(__name__)

def exit_gracefully(signal, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    print('shut down')
    # BackgroundHandler().stop()
    sys.exit(1)

signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGABRT, exit_gracefully)
signal.signal(signal.SIGALRM, exit_gracefully)
signal.signal(signal.SIGBUS, exit_gracefully)
signal.signal(signal.SIGCHLD, exit_gracefully)
signal.signal(signal.SIGCONT, exit_gracefully)
signal.signal(signal.SIGEMT, exit_gracefully)
signal.signal(signal.SIGFPE, exit_gracefully)
signal.signal(signal.SIGHUP, exit_gracefully)
signal.signal(signal.SIGIO, exit_gracefully)
signal.signal(signal.SIGIOT, exit_gracefully)
signal.signal(signal.SIGPIPE, exit_gracefully)
signal.signal(signal.SIGPROF, exit_gracefully)
signal.signal(signal.SIGQUIT, exit_gracefully)
signal.signal(signal.SIGSEGV, exit_gracefully)
signal.signal(signal.SIGSYS, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGTRAP, exit_gracefully)
signal.signal(signal.SIGTSTP, exit_gracefully)
signal.signal(signal.SIGTTIN, exit_gracefully)
signal.signal(signal.SIGTTOU, exit_gracefully)
signal.signal(signal.SIGURG, exit_gracefully)
signal.signal(signal.SIGUSR1, exit_gracefully)
signal.signal(signal.SIGUSR2, exit_gracefully)
signal.signal(signal.SIGVTALRM, exit_gracefully)
signal.signal(signal.SIGWINCH, exit_gracefully)
signal.signal(signal.SIGXCPU, exit_gracefully)
signal.signal(signal.SIGXFSZ, exit_gracefully)

# signal.signal(signal.SIGTERM, lambda num, frame: sys.exit(0))

# def sigint_handler(*args):
#     """Handler for the SIGINT signal."""
#     sys.stderr.write('\r')
#     if QMessageBox.question(None, '', "Are you sure you want to quit?",
#                             QMessageBox.Yes | QMessageBox.No,
#                             QMessageBox.No) == QMessageBox.Yes:
#         QApplication.quit()



# def set_signals():
#     signal.signal(signal.SIGINT, exit_gracefully)
#     signal.signal(signal.SIGTERM, exit_gracefully)
#     signal.signal(signal.SIGALRM, exit_gracefully)
#     signal.signal(signal.SIGHUP, signal.SIG_IGN)
#     print('Press Ctrl+C')


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
    try:
        r = requests.get(settings.MIN_VERSION_URL)
    except requests.exceptions.ConnectionError:
        running_warning(message='Check for minimum version requirements for OSF-Sync failed '
                                'because you have no Internet connection', critical=True)
    else:
        try:
            min_version = r.json()['min-version']
        except KeyError as e:
            logger.exception(e)

    if min_version:
        if StrictVersion(settings.VERSION) < StrictVersion(min_version):
            # User error message
            running_warning(message='You must update to a newer version. '
                                    'You can find newest version at {}'
                            .format(settings.OFFLINE_PROJECT_ON_OSF),
                            critical=True)
            sys.exit(1)

    # Start logging all events
    if '--drop' in sys.argv:
        drop_db()

    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, 'Systray', 'Could not detect a system tray on this system')
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)
    sync_app = OSFOfflineQT(app)
    if not sync_app.start():
        return sys.exit(1)
    return sys.exit(app.exec_())


if __name__ == "__main__":
    # signal.signal(signal.SIGINT, sigint_handler)
    # app = QApplication(sys.argv)
    # timer = QTimer()
    # timer.start(500)  # You may change this if you wish.
    # timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.
    start()
    # sys.exit(app.exec_())
