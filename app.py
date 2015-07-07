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


from views.Preferences import Preferences
from views.SystemTray import SystemTray
from controller import OSFController

def ensure_event_loop():
    """Ensure the existance of an eventloop
    Useful for contexts where get_event_loop() may
    raise an exception.
    :returns: The new event loop
    :rtype: BaseEventLoop
    """
    try:
        return asyncio.get_event_loop()
    except (AssertionError, RuntimeError):
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Note: No clever tricks are used here to dry up code
    # This avoids an infinite loop if settings the event loop ever fails
    return asyncio.get_event_loop()


def __coroutine_unwrapper(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return ensure_event_loop().run_until_complete(func(*args, **kwargs))
    wrapped.as_async = func
    return wrapped


@asyncio.coroutine
def backgrounded(func, *args, **kwargs):
    """Runs the given function with the given arguments in
    a background thread
    """
    loop = asyncio.get_event_loop()
    if asyncio.iscoroutinefunction(func):
        func = __coroutine_unwrapper(func)

    return (yield from loop.run_in_executor(
        None,  # None uses the default executer, ThreadPoolExecuter
        functools.partial(func, *args, **kwargs)
    ))


def backgroundify(func):
    @asyncio.coroutine
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return (yield from backgrounded(func, *args, **kwargs))
    return wrapped



class OSFApp(QDialog):
    def __init__(self):
        super().__init__()

        #settings
        self.appname = "OSF Offline"
        self.appauthor = "COS"


        #controller
        self.controller = OSFController(appname=self.appname, appauthor=self.appauthor)
        import pdb;pdb.set_trace()
        #views
        self.tray = SystemTray()
        #todo: remove priority abilities
        self.preferences = Preferences(self.controller.containingFolder, None)

        #connect all signal-slot pairs
        self.setupConnections()

        # start all work
        # backgroundify(self.controller.start(ensure_event_loop()))


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
                "Could not detect a system tray on this system")
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)
    app.setStyle('cleanlooks')



    osf = OSFApp()
    osf.hide()
    app.exec_()




    


