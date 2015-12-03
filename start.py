#!/usr/bin/env python
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QDialog

from osfoffline.utils.singleton import SingleInstance
from osfoffline.application.main import OSFApp
from osfoffline.database import drop_db
from osfoffline.views.login import LoginScreen


def running_warning():
    warn_app = QApplication(sys.argv)
    QMessageBox.information(None, 'Systray', 'OSF-Offline is already running. Check out the system tray.')
    warn_app.quit()


def start():
    SingleInstance(callback=running_warning)  # will end application if an instance is already running

    # Start logging all events
    if '--drop' in sys.argv:
        drop_db()

    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, 'Systray', 'Could not detect a system tray on this system')
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    if LoginScreen().exec_() == QDialog.Accepted:
        osf = OSFApp()

        osf.start()

        osf.hide()
        sys.exit(app.exec_())

    return sys.exit(1)


if __name__ == "__main__":
    start()
