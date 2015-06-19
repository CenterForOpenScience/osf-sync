#!/usr/bin/env python



import logging
import os
import json
import os.path
import sys
import subprocess
import webbrowser

from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QSystemTrayIcon,
                             QFileDialog)
from PyQt5.QtCore import QCoreApplication
from appdirs import *
from watchdog.observers import Observer

# from CustomEventHandler import CustomEventHandler
from views.Preferences import Preferences
from views.SystemTray import SystemTray
from controller import OSFController



class OSFApp(QDialog):
    def __init__(self):
        super().__init__()

        #settings
        self.appname = "OSF Offline"
        self.appauthor = "COS"


        #controller
        self.controller = OSFController(appname=self.appname, appauthor=self.appauthor)

        #views
        self.tray = SystemTray()
        self.preferences = Preferences(self.controller.containingFolder, self.controller.event_handler.data['data'])

        #connect all signal-slot pairs
        self.setupConnections()



    def setupConnections(self):
        # [ (signal, slot) ]
        signal_slot_pairs = [
            #system tray
            (self.tray.openProjectFolderAction.triggered, self.controller.openProjectFolder),
            (self.tray.launchOSFAction.triggered, self.controller.startOSF),
            (self.tray.currentlySynchingAction.triggered, self.controller.currentlySynching),
            (self.tray.priorityAction.triggered, self.openPriorityScreen),
            (self.tray.preferencesAction.triggered, self.openPreferences),
            (self.tray.aboutAction.triggered, self.startAboutScreen),
            (self.tray.quitAction.triggered, self.controller.teardown),

            #preferences
            # (self.preferences.preferencesWindow.changeFolderButton.clicked, self.preferences.openContainingFolderPicker)
        ]
        for signal, slot in signal_slot_pairs:
            signal.connect(slot)




    def openPriorityScreen(self):
        self.preferences.openWindow(Preferences.PRIORITY)

    def openPreferences(self):
        self.preferences.openWindow(Preferences.GENERAL)

    def startAboutScreen(self):
        self.preferences.openWindow(Preferences.ABOUT)




if __name__ == '__main__':
    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                "I couldn't detect any system tray on this system.")
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)




    osf = OSFApp()
    osf.hide()
    app.exec_()




    


