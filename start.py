import os
import sys

from PyQt5.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon)
from osfoffline.application.main import OSFApp
from osfoffline import utils
from server import SingleInstance

def start():
    # Start logging all events
    utils.start_app_logging()
    if os.name == 'nt':
        single_app = SingleInstance()

        if single_app.aleradyrunning():
            QMessageBox.critical(
                None,
                "Systray",
                "OSF-Offline is already running. Check out the system tray."
            )
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
