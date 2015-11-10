import os
import sys

from PyQt5.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon)
from osfoffline.application.main import OSFApp
from osfoffline import utils


def start():
    # Start logging all events
    utils.start_app_logging()
    if os.name == 'nt':
        from server import SingleInstance
        single_app = SingleInstance()

        if single_app.aleradyrunning():
            warn_app = QApplication(sys.argv)
            QMessageBox.critical(
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
