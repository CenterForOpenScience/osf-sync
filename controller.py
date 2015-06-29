import logging
import os
import json
import os.path
import sys
import subprocess
import webbrowser
import models
from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QSystemTrayIcon,
                             QFileDialog)
from PyQt5.QtCore import QCoreApplication, QFileSystemWatcher
from appdirs import *
from watchdog.observers import Observer
import Polling
from OSFEventHandler import OSFEventHandler
from views import Preferences

__author__ = 'himanshu'
class OSFController(QDialog):

    def __init__(self, appname, appauthor, ):
        super().__init__()
        self.appname=appname
        self.appauthor=appauthor

        self.createConfig()
        import threading; print('---inside osfcontroller init-----{}----'.format(threading.current_thread()))


        self.session = models.get_session()
        self.user = self.getCurrentUser() #creates session
        import threading; print('---inside osfcontroller init2-----{}----'.format(threading.current_thread()))
        self.poller = Polling.Poll(self.config['dbdir'], self.user.osf_id, self.session)


        self.containingFolder = "/home/himanshu/OSF-Offline/dumbdir" # todo: remove. only for dev.
        if not self.containingFolderIsSet():
            self.setContainingFolder()
        #todo: handle if OSF folder does not exist. OR if user wants custom OSF folder
        self.OSFFolder = self.user.osf_path #os.path.join(self.containingFolder, "OSF") # todo: store osf folder
        self.startObservingOSFFolder()
        self.startPollingServer()
        self.startLogging()



        # self.preferences = Preferences(self.containingFolder, self.event_handler.data['data'])

    def startPollingServer(self):
        # self.poller = Polling.Poll(self.config['dbdir'], self.user)
        self.poller.start()
        # self.poller.run()

    def stopPollingServer(self):
        self.poller.stop()
        self.poller.join()


    def getCurrentUser(self):

        import threading; print('---inside getcurrentuser-----{}----'.format(threading.current_thread()))
        user = self.session.query(models.User).filter(models.User.fullname == "Jack Frost").first()

        if not user:
            user = models.User(fullname="Jack Frost", osf_id='xc3u4', osf_login='Tinticulge1932@armyspy.com', osf_path='/home/himanshu/OSF-Offline/dumbdir/OSF', oauth_token='FAKE', osf_password='password')
            self.session.add(user)
            try:
                self.session.commit()
            except:
                self.session.rollback()
                raise
        # local_user = None
        # local_user.fullname = user.fullname
        # session.close()
        return user


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


        # logging.getLogger('sqlalchemy.engine').addHandler()



    def startObservingOSFFolder(self):


        #if something inside the folder changes, log it to config dir
        #if something inside the folder changes, show it on console.
        path = self.OSFFolder #set this to whatever appdirs says - data_dir
        self.event_handler = OSFEventHandler(path, self.config['dbdir'],self.user ) #create event handler
        #if config actually has legitimate data. use it.
        # if self.config != {}:
        #     self.event_handler.import_from_db(items_dict=self.config, user='himanshu', password='pass', name='himanshu', fav_movie='matrix', fav_show='simpsons')

        #start
        self.observer = Observer() #create observer. watched for events on files.
        #attach event handler to observed events. make observer recursive
        self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.start() #start

    def stopObservingOSFFolder(self):
        self.observer.stop()


    def closeEvent(self, event):
        if self.trayIcon.isVisible():
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
            self.setContainingFolder()

    def containingFolderIsSet(self):
        try:
            return os.path.isdir(self.containingFolder)
        except ValueError:
            return False


    def setContainingFolder(self, newContainingFolder=None):
        if newContainingFolder is None:
            self.containingFolder = QFileDialog.getExistingDirectory(self, "Choose folder")
        else:
            self.containingFolder = newContainingFolder


    def startOSF(self):
        url = "http://osf.io/"
        webbrowser.open_new_tab(url)






    def currentlySynching(self):
        #todo: can use this sudo code to make proper
        # if syncQueue.empty():
        #     text = "Up to date"
        # else:
        #     text = "currently {}".format(syncQueue.top().name())
        import datetime
        text = "Up to date ({})".format(str(datetime.datetime.now()))
        self.currentlySynchingAction.setText(0,text)


    def teardown(self):

        # store current configs in config file
        dir = user_config_dir(self.appname, self.appauthor)
        rel_osf_config = os.path.join(dir,'config.osf')
        file = open(rel_osf_config,'w+')
        file.truncate(0)
        file.write(json.dumps(self.config))
        file.close()

        # stop polling the server
        self.stopPollingServer()

        # stop observing OSF folder
        self.stopObservingOSFFolder()

        #quit the application
        QApplication.instance().quit()


    def createConfig(self):
        #todo: create helper function to check if config/data/OSF/... dirs' exist, and create them if they dont' exist.

        #check if dir has config file already in it, if so use it. if not create it.
        dir = user_config_dir(self.appname, self.appauthor)
        rel_osf_config = os.path.join(dir,'config.osf')
        #ensure directory exists
        if not os.path.exists(dir):
            os.makedirs(dir)

        #ensure data dir exists
        data_dir = user_data_dir(self.appname, self.appauthor)

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        models.setup_db(data_dir)
        # models.create_models(dir= data_dir)

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
            #todo: figure out where this should actually be
            self.config={}
            self.config['appname'] = self.appname
            self.config['appauthor'] = self.appauthor
            self.config['dbdir'] = user_data_dir(self.appname, self.appauthor)
        print(self.config)
