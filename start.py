import os
import sys
import __main__

from PyQt5.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon)
from osfoffline.application.main import OSFApp
from osfoffline import utils


def isOnlyInstance():
    # Determine if there are more than the current instance of the application
    # running at the current time.
    return os.system("(( $(ps -ef | grep python | grep '[" +
                     __main__.__file__[0] + "]" + __main__.__file__[1:] +
                     "' | wc -l) > 1 ))") != 0


def start():
    # Start logging all events
    utils.start_app_logging()
    if sys.platform == 'win32':
        from server import SingleInstance
        single_app = SingleInstance()

        if single_app.aleradyrunning():
            warn_app = QApplication(sys.argv)
            QMessageBox.information(
                None,
                "Systray",
                "OSF-Offline is already running. Check out the system tray."
            )
            warn_app.quit()
            exit(0)
    elif sys.platform == 'darwin':
        if not isOnlyInstance():
            warn_app = QApplication(sys.argv)
            QMessageBox.information(
                None,
                "Systray",
                "OSF-Offline is already running. Check out the system tray."
            )
            warn_app.quit()
            exit(0)

    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "Systray",
            "Could not detect a system tray on this system"
        )
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    osf = OSFApp()
    osf.start()

    osf.hide()
    app.exec_()


if __name__ == "__main__":
    start()
