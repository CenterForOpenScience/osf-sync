#!/usr/bin/env python
import threading
from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QSystemTrayIcon)
from PyQt5.QtCore import QSettings
from osfoffline.views.preferences import Preferences
from osfoffline.views.system_tray import SystemTray
from osfoffline.controller import OSFController
from osfoffline.views.start_screen import StartScreen
import osfoffline.alerts as AlertHandler
import sys


RUN_PATH = "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"


class OSFApp(QDialog):
    def __init__(self):
        super().__init__()

        # settings

        self.app_name = "OSFOffline"
        self.app_author = "COS"

        # controller
        self.controller = OSFController(app_name=self.app_name, app_author=self.app_author)

        # views
        self.start_screen = StartScreen()
        self.tray = SystemTray()
        self.preferences = Preferences(self.controller.containing_folder)
        AlertHandler.setup_alerts(self.tray.tray_icon)

        # connect all signal-slot pairs
        self.setup_connections()

        # self.thread = threading.Thread(target=self.controller.start)

    def start(self):
        self.controller.start()

    def setup_connections(self):
        # [ (signal, slot) ]
        signal_slot_pairs = [

            # system tray
            (self.tray.open_osf_folder_action.triggered, self.controller.open_osf_folder),
            (self.tray.launch_osf_action.triggered, self.controller.start_osf),
            # (self.tray.currently_synching_action.triggered, self.controller.currently_synching),
            (self.tray.preferences_action.triggered, self.open_preferences),
            (self.tray.about_action.triggered, self.start_about_screen),

            (self.tray.quit_action.triggered, self.controller.quit),

            # controller events
            (self.controller.login_signal, self.start_screen.open_window),
            (self.controller.start_tray_signal, self.tray.start),
            (self.controller.containing_folder_updated_signal, self.preferences.update_containing_folder_text),

            # preferences
            (self.preferences.preferences_window.desktopNotifications.stateChanged, self.alerts_changed),
            (self.preferences.preferences_window.startOnStartup.stateChanged, self.startup_changed),
            (self.preferences.preferences_window.changeFolderButton.clicked, self.controller.set_containing_folder_process),
            (self.preferences.preferences_closed_signal, self.controller.resume),
            (self.preferences.preferences_window.accountLogOutButton.clicked, self.controller.logout),


            # start screen
            (self.start_screen.done_logging_in_signal, self.controller.start),
            (self.start_screen.quit_application_signal, self.controller.quit),

        ]
        for signal, slot in signal_slot_pairs:
            signal.connect(slot)



    def open_preferences(self):
        # todo: preferences button should open general page
        # todo: make sure open_window(Prefernces.OSF) is called whenever you go to osf page.
        self.controller.pause()
        self.preferences.open_window(Preferences.GENERAL)

    def start_about_screen(self):
        self.controller.pause()
        self.preferences.open_window(Preferences.ABOUT)


    def alerts_changed(self):
        if self.preferences.preferences_window.desktopNotifications.isChecked():
            AlertHandler.show_alerts = True
        else:
            AlertHandler.show_alerts = False

    def startup_changed(self):
        # todo: probably should give notification to show that this setting has been changed.

        if self.preferences.preferences_window.startOnStartup.isChecked():
            # todo: make it so that this application starts on login
            # self.settings = QSettings(RUN_PATH, QSettings.NativeFormat)
            pass

        else:
            # todo: make it so that this application does NOT start on login
            pass

def start():
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
