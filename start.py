import sys

from PyQt5.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon)
from osfoffline.application.main import OSFApp
from osfoffline import utils

def running_warning():
    warn_app = QApplication(sys.argv)
    QMessageBox.information(
        None,
        "Systray",
        "OSF-Offline is already running. Check out the system tray."
    )
    warn_app.quit()

def start():
    # Start logging all events
    utils.start_app_logging()
    from osfoffline.utils.singleton import SingleInstance
    me = SingleInstance(callback=running_warning)  # will end application if an instance is already running

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
