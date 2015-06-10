#!/usr/bin/env python



from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
        QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QMenu, QPushButton, QSpinBox, QStyle, QSystemTrayIcon,
        QTextEdit, QVBoxLayout, QFileDialog, QMainWindow)

from appdirs import *
import logging
from watchdog.observers import Observer
import os
import json
import os.path
from CustomEventHandler import CustomEventHandler
import sys
import rsc.systray_rc # REQUIRED FOR GUI
from rsc.preferences_rc import Ui_Preferences # REQUIRED FOR GUI
import subprocess
import webbrowser





class OSFController(QDialog):
    def __init__(self):
        super().__init__()
        self.appname = "OSF Offline"
        self.appauthor = "COS"

        self.createActions()
        self.createTrayIcon()
        self.createConfig()
        self.containingFolder = "/home/himanshu/OSF-Offline/dumbdir" #todo: remove. only for dev.
        # self.projectFolder = os.path.join(self.containingFolder, self.projectName)
        if not self.containingFolderIsSet():
            self.setContainingFolder()
        self.startObservingContainingFolder()
        self.startLogging()







    def startLogging(self):
        #make sure logging directory exists
        log_dir = user_log_dir(self.appname, self.appauthor)
        if not os.path.exists(log_dir): # ~/.cache/appname
            os.makedirs(log_dir)
        if not os.path.exists(os.path.join(log_dir,'log')): # ~/.cache/appname/log (this is what logging uses)
            os.makedirs(os.path.join(log_dir,'log'))


        #make sure logging file exists
        log_file = open(os.path.join(log_dir,'osf.log'),'w+')
        log_file.close()

        #set up config. set up format of logged info. set up "level of logging" which i think is just how urgent the logging thing is. probably just a tag to each event.
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            filename = os.path.join(log_dir,'osf.log'),
                            filemode='w')
        # define a Handler which writes INFO messages or higher to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        # tell the handler to use this format
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

    def containingFolderIsSet(self):
        try:
            os.path.isdir(self.containingFolder)
            return True
        except AttributeError: # self.containingFolder doesn't exist
            return False

    def startObservingContainingFolder(self):
        #if something inside the folder changes, log it to config dir
        #if something inside the folder changes, show it on console.
        path = self.containingFolder #set this to whatever appdirs says - data_dir
        print(path)
        event_handler = CustomEventHandler(path) #create event handler
        #if config actually has legitimate data. use it.
        if self.config != {}:
            event_handler.import_from_db(items_dict=self.config, user='himanshu', password='pass', name='himanshu', fav_movie='matrix', fav_show='simpsons')

        #start
        self.observer = Observer() #create observer. watched for events on files.
        #attach event handler to observed events. make observer recursive
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start() #start

    def stopObservingContainingFolder(self):
        self.observer.stop()


    def closeEvent(self, event):
        if self.trayIcon.isVisible():
            QMessageBox.information(self, "Systray",
                    "The program will keep running in the system tray. To "
                    "terminate the program, choose <b>Quit</b> in the "
                    "context menu of the system tray entry.")
            self.hide()
            event.ignore()



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



    def createActions(self):
        self.openProjectFolderAction = QAction("Open Project Folder", self, triggered=self.openProjectFolder)
        self.launchOSFAction = QAction("Launch OSF", self, triggered=self.startOSF)
        self.currentlySynchingAction = QAction("Up to date", self, triggered=self.currentlySynching)
        #todo: figure out how to triger currentlySynching
        # self.currentlySynchingAction.hover()
        # self.currentlySynchingAction.setDisabled(True)
        self.preferencesAction = QAction("Preferences", self, triggered=self.openPreferencesAction)
        self.aboutAction = QAction("&About", self, triggered=self.startAboutScreen)
        self.quitAction = QAction("&Quit", self,
                triggered=self.teardown)


    def openProjectFolder(self):
        if self.containingFolderIsSet():
            if sys.platform=='win32':
                os.startfile(self.containingFolder)
            elif sys.platform=='darwin':
                subprocess.Popen(['open', self.containingFolder])
            else:
                try:
                    subprocess.Popen(['xdg-open', self.containingFolder])
                except OSError:
                    # er, think of something else to try
                    # xdg-open *should* be supported by recent Gnome, KDE, Xfce
                    pass #todo: what to do in this case?
        else:
            self.setCcontainingFolder()

    def setContainingFolder(self):
        self.containingFolder = QFileDialog.getExistingDirectory(self, "Choose folder")

    def startOSF(self):
        pid = 'dk6as'
        url = "http://osf.io/{}/".format(pid)
        webbrowser.open_new_tab(url)

    def startPriorityScreen(self):
        pass

    def currentlySynching(self):
        print(1)
        #todo: can use this sudo code to make proper
        # if syncQueue.empty():
        #     text = "Up to date"
        # else:
        #     text = "currently {}".format(syncQueue.top().name())
        import datetime
        text = "Up to date ({})".format(str(datetime.datetime.now()))
        self.currentlySynchingAction.setText(text)

    def openPreferencesAction(self):
        preferencesWindow = Ui_Preferences()
        preferencesWindow.setupUi(self)
        self.show()

    def startAboutScreen(self):
        pass


    def teardown(self):
        dir = user_config_dir(self.appname, self.appauthor)
        rel_osf_config = os.path.join(dir,'config.osf')
        file = open(rel_osf_config,'w+')
        file.truncate(0)
        file.write(json.dumps(self.config))
        file.close()

        QApplication.instance().quit()

    def createTrayIcon(self):

        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.openProjectFolderAction)
        self.trayIconMenu.addAction(self.launchOSFAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.currentlySynchingAction)
        #todo: figure out how to trigger currentlySynchingAction
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.preferencesAction)
        self.trayIconMenu.addAction(self.aboutAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)
        self.trayIcon = QSystemTrayIcon(self)
        # self.trayIcon.activated.connect(self.iconActivated)
        self.trayIcon.setContextMenu(self.trayIconMenu)


        #todo: hate this icon. make better.
        icon = QIcon(':/images/cos_logo.png')
        self.trayIcon.setIcon(icon)
        self.trayIcon.messageClicked.connect(self.messageClicked)
        self.trayIcon.activated.connect(self.iconActivated)
        self.trayIcon.show()

    def createConfig(self):

        #check if dir has config file already in it, if so use it. if not create it.
        dir = user_config_dir(self.appname, self.appauthor)
        rel_osf_config = os.path.join(dir,'config.osf')
        #ensure directory exists
        if not os.path.exists(dir):
            os.makedirs(dir)

        #new file if file doesnt exist.
        try:
            file = open(rel_osf_config,'r+w')
        except:
            file = open(rel_osf_config,'w+')
        try:
            #todo: actually start adding to self.config so that it is not corrupt on startup
            file_content = file.read()
            self.config = json.loads(file_content)
        except ValueError:
            print('config file is corrupted. Creating new config file')
            self.config ={}
        print(self.config)




if __name__ == '__main__':
    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                "I couldn't detect any system tray on this system.")
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)




    osf = OSFController()
    osf.hide()
    app.exec_()




    


