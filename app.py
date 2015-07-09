#!/usr/bin/env python



import logging
import os
import json
import os.path
import sys
import subprocess
import webbrowser
import asyncio
import functools
from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QSystemTrayIcon,
                             QFileDialog)
from PyQt5.QtCore import QCoreApplication
from appdirs import *
from watchdog.observers import Observer
import threading

from views.Preferences import Preferences
from views.SystemTray import SystemTray
from controller import OSFController
from views.StartScreen import StartScreen
import alerts

class OSFApp(QDialog):
    def __init__(self):
        super().__init__()

        #settings
        self.appname = "OSF Offline"
        self.appauthor = "COS"


        #controller
        self.controller = OSFController(appname=self.appname, appauthor=self.appauthor)

        #views
        self.startScreen = StartScreen()
        self.tray = SystemTray()
        #todo: remove priority abilities
        self.preferences = Preferences(self.controller.containingFolder, None)
        alerts.setup_alerts(self.tray.trayIcon)

        #connect all signal-slot pairs
        self.setupConnections()


    def start(self):
        # start all work
        t = threading.Thread(target=self.controller.start)
        t.start()
        # backgroundify(self.controller.start())

    def setupConnections(self):
        # [ (signal, slot) ]
        signal_slot_pairs = [
            # system tray
            (self.tray.openProjectFolderAction.triggered, self.controller.openProjectFolder),
            (self.tray.launchOSFAction.triggered, self.controller.startOSF),
            (self.tray.currentlySynchingAction.triggered, self.controller.currentlySynching),
            (self.tray.priorityAction.triggered, self.openPriorityScreen),
            (self.tray.preferencesAction.triggered, self.openPreferences),
            (self.tray.aboutAction.triggered, self.startAboutScreen),
            (self.tray.quitAction.triggered, self.controller.teardown),

            # controller events
            (self.controller.loginAction.triggered, self.startScreen.openWindow),

            #preferences
            # (self.preferences.preferencesWindow.changeFolderButton.clicked, self.preferences.openContainingFolderPicker)

            # start screen
            (self.startScreen.doneLoggingInAction.triggered, self.controller.start)
        ]
        for signal, slot in signal_slot_pairs:
            signal.connect(slot)




    def openPriorityScreen(self):
        self.preferences.openWindow(Preferences.PRIORITY)

    def openPreferences(self):
        self.preferences.openWindow(Preferences.GENERAL)

    def startAboutScreen(self):
        self.preferences.openWindow(Preferences.ABOUT)

    def openLogInScreen(self):
        self.preferences.openWindow(Preferences.OSF)




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




    


