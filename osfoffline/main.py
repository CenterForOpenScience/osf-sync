#!/usr/bin/env python
import threading
from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QSystemTrayIcon)
from views.preferences import Preferences
from views.system_tray import SystemTray
from controller import OSFController
from views.start_screen import StartScreen
from alerts import Alert
import sys


class OSFApp(QDialog):
    def __init__(self):
        super().__init__()

        # settings
        self.app_name = "OSF Offline"
        self.app_author = "COS"

        # controller
        self.controller = OSFController(app_name=self.app_name, app_author=self.app_author)

        # views
        self.start_screen = StartScreen()
        self.tray = SystemTray()
        # todo: remove priority abilities
        self.preferences = Preferences(self.controller.containing_folder)
        self.alerts = Alert(self.tray.tray_icon, self.controller.loop)

        # connect all signal-slot pairs
        self.setup_connections()

        # self.thread = threading.Thread(target=self.controller.start)

    def start(self):
        self.alerts.start()
        t = threading.Thread(target=self.controller.start)
        t.start()

    # todo: finish this!!
    # def start(self):
    #     # start all work
    #     import threading; print('starting thread with id:{}'.format(self.thread.name))
    #     self.thread.start()
    #     # backgroundify(self.controller.start())
    #
    # def startStartScreen(self):
    #     """
    #     Issue is that new user goes to login and then
    #     :return:
    #     """
    #     print(1)
    #     self.thread.join()
    #     print(2)
    #     # can't restart threads. Easy way to handle this is to just recreate a thread after stopping previous one.
    #     self.thread = threading.Thread(target=self.controller.start)
    #     print(3)
    #     self.startScreen.openWindow()
    #     print(4)

    def setup_connections(self):
        # [ (signal, slot) ]
        signal_slot_pairs = [
            # system tray
            (self.tray.open_project_folder_action.triggered, self.controller.open_project_folder),
            (self.tray.launch_osf_action.triggered, self.controller.start_osf),
            (self.tray.currently_synching_action.triggered, self.controller.currently_synching),
            (self.tray.priority_action.triggered, self.open_priority_screen),
            (self.tray.preferences_action.triggered, self.open_preferences),
            (self.tray.about_action.triggered, self.start_about_screen),
            (self.tray.quit_action.triggered, self.controller.teardown),

            # controller events
            (self.controller.login_action.triggered, self.start_screen.open_window),

            # preferences
            # (self.preferences.preferencesWindow.changeFolderButton.clicked, self.preferences.openContainingFolderPicker)

            # start screen
            (self.start_screen.done_logging_in_action.triggered, self.controller.start)
        ]
        for signal, slot in signal_slot_pairs:
            signal.connect(slot)

    def open_priority_screen(self):
        self.preferences.open_window(Preferences.PRIORITY)

    def open_preferences(self):
        self.preferences.open_window(Preferences.GENERAL)

    def start_about_screen(self):
        self.preferences.open_window(Preferences.ABOUT)

    def open_log_in_screen(self):
        self.preferences.open_window(Preferences.OSF)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                             "Could not detect a system tray on this system")
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    osf = OSFApp()
    osf.start()

    osf.hide()
    app.exec_()
