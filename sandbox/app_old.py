__author__ = 'himanshu'
from PyQt5.QtGui import QIcon,QColor
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
        QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QMenu, QPushButton, QSpinBox, QStyle, QSystemTrayIcon,
        QTextEdit, QVBoxLayout, QMainWindow)
from PyQt5.QtCore import pyqtSlot,QObject

import systray_rc
from appdirs import *
import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
import os
import json
import os.path




class OSFApp(QDialog):
    def __init__(self,  *args):
        super().__init__()

        #actions
        self.initActions()

        #views
        self.initView()

    def initActions(self):
        self.actions = {}

        #create individual actions
        self.chooseSyncFolderAction = QAction("Choose Sync Folder", self, triggered=self.hide)
        self.quitAction = QAction("&Quit", self,
                triggered=QApplication.instance().quit)

        #add all actions to actions dict
        self.actions['quit'] = self.quitAction
        self.actions['chooseFolder'] = self.chooseSyncFolderAction

    def initView(self):
        self.view = OSFView( self.doc, self)
        self.setCentralWidget(self.view)






# class OSFDoc(QObject):
#
#     def __init__(self, *args):
#         super(*args)
#         self.modified=False
#
#     def slotModify(self):
#         self.modified = not self.modified
#         self.emit(self.modified)
#         # act = QAction("Action", self, triggered=self.on_triggered)
#         # self.emit(PYSIGNAL("sigDocModified"),
#         #           (self.modified,))
#
#     def isModified(self):
#         return self.modified

class OSFView(QDialog):
    def __init__(self, doc, *args):
        super().__init__(*args)
        self.doc = doc
        # self.connect(self.slotDocModified)
        # self.slotDocModified(self.doc.isModified())
        self.createTrayIcon()

        #slots
        # self.trayIcon.messageClicked.connect(self.messageClicked)
        # self.trayIcon.activated.connect(self.iconActivated)


        self.connect(self.doc, PYSIGNAL("sigDocModified"),
                      self.slotDocModified)
        self.slotDocModified(self.doc.isModified())

        #start
        self.trayIcon.show()

    @pyqtSlot(int)
    def slotDocModified(self, value):
        if value:
            self.setBackgroundColor(QColor("red"))
        else:
            self.setBackgroundColor(QColor("green"))



    def createTrayIcon(self):

        self.trayIconMenu = QMenu(self)

        # self.trayIconMenu.addAction(self.chooseSyncFolderAction)
        self.trayIconMenu.addSeparator()
        # self.trayIconMenu.addAction(self.quitAction)
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)

        icon = QIcon(':/images/heart.png')
        self.trayIcon.setIcon(icon)

    def iconActivated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.iconComboBox.setCurrentIndex(
                    (self.iconComboBox.currentIndex() + 1)
                    % self.iconComboBox.count())
        elif reason == QSystemTrayIcon.MiddleClick:
            self.showMessage()

    def showMessage(self):
        icon = QSystemTrayIcon.MessageIcon(
                self.typeComboBox.itemData(self.typeComboBox.currentIndex()))
        self.trayIcon.showMessage(self.titleEdit.text(),
                self.bodyEdit.toPlainText(), icon,
                self.durationSpinBox.value() * 1000)

    def messageClicked(self):
        QMessageBox.information(None, "Systray",
                "Sorry, I already gave what help I could.\nMaybe you should "
                "try asking a human?")


def main(args):
    app=QApplication(args)
    QApplication.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                "I couldn't detect any system tray on this system.")
        sys.exit(1)
    osf = OSFApp()
    # app.setMainWidget(osf) #from love_actually, it looks like the window just knows.ehhh.
    osf.show()
    # app.exec_loop()
    app.exec_()

if __name__=="__main__":
    main(sys.argv)