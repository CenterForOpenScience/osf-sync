import logging
import os
import json
import os.path
import sys
import subprocess
import webbrowser
import models
from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QSystemTrayIcon,
                             QFileDialog, QAction)
from PyQt5.QtCore import QCoreApplication, QFileSystemWatcher
from appdirs import *
from watchdog.observers import Observer
import Polling
from OSFEventHandler import OSFEventHandler
from views import Preferences
import asyncio
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

__author__ = 'himanshu'

class OSFController(QDialog):

    def __init__(self, appname, appauthor, ):
        super().__init__()
        # logging.basicConfig(level=logging.DEBUG)
        self.appname=appname
        self.appauthor=appauthor

        self.containingFolder = ''

        self.loginAction = QAction("Open Login Screen", self)
        self.multipleUserAction = QAction("Choose Logged In User", self)


    def start(self):
        self.loop = self.ensure_event_loop()
        self.createConfigs()
        self.session = models.get_session()
        self.user = self.getCurrentUser()
        if self.user:
            self.containingFolder = os.path.dirname(self.user.osf_path)
            if not self.containingFolderIsSet():
                self.setContainingFolder()
            self.user.osf_path = os.path.join(self.containingFolder,"OSF")
            self.save(self.user)

            #todo: handle if OSF folder does not exist. OR if user wants custom OSF folder
            if not os.path.isdir(self.user.osf_path):
                os.makedirs(self.user.osf_path)
            self.startLogging()
            self.OSFFolder = self.user.osf_path
            self.startObservingOSFFolder()
            # self.preferences = Preferences(self.containingFolder, self.event_handler.data['data'])
            self.startPollingServer()
            self.loop.run_forever()



    def startPollingServer(self):
        #todo: can probably change this to just pass in the self.user
        self.poller = Polling.Poll(self.user.osf_id, self.loop)
        self.poller.start()


    def stopPollingServer(self):
        self.poller.stop()
        # self.poller.join()

    #todo: when log in is working, you need to make this work with log in screen.
    def getCurrentUser(self):
        user = None
        import threading; print('---inside getcurrentuser-----{}----'.format(threading.current_thread()))
        try:
            user = self.session.query(models.User).filter(models.User.logged_in == True).one()
        except MultipleResultsFound:
            # todo: multiple user screen allows you to choose which user is logged in
            print('multiple users are logged in currently. We want only one use to be logged in.')
            print('for now, we will just choose the first user in the db to be the logged in user')
            print('also, we will log out all other users.')
            # for user in self.session.query(models.User):
            #     user.logged_in = False
            #     self.save(user)
            # user = self.session.query(models.User).first()
            # user.logged_in = True
            # self.save(user)
            self.multipleUserAction.trigger()
        except NoResultFound:
            # todo: allows you to log in (creates an account in db and logs it in)
            self.loginAction.trigger()
            print('no users are logged in currently. Logging in first user in db.')
            # user = self.session.query(models.User).first()
            # if not user:
            #     print('no users at all in the db. creating one and logging him in')
            #     user = models.User(
            #         fullname="Johnny Appleseed",
            #         osf_id='p42te',
            #         osf_login='rewhe1931@gustr.com',
            #         osf_path='/home/himanshu/OSF-Offline/dumbdir/OSF',
            #         oauth_token='eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLkJiQkg0TzhIYXMzU0dzQlNPQ29MYUEuSTRlRG4zcmZkNV92b1hJdkRvTmhodjhmV3M1Ql8tYUV1ZmJIR3ZZbkF0X1lPVDJRTFhVc05rdjJKZUhlUFhfUnpvZW1ucW9aN0ZlY0FidGpZcmxRR2hHem5IenRWREVQYWpXSmNnVVhtQWVYLUxSV25ENzBqYk9YczFDVHJKMG9BV29Fd3ZMSkpGSjdnZ29QVVBlLTJsX2NLcGY4UzZtaDRPMEtGX3lBRUlLTjhwMEdXZ3lVNWJ3b0lhZU1FSTVELllDYTBaTm5lSVFkSzBRbDNmY2pkZGc.dO-5NcN9X6ss7PeDt5fWRpFtMomgOBjPPv8Qehn34fJXJH2bCu9FIxo4Lxhja9dYGmCNAtc8jn05FjerjarQgQ',
            #         osf_password='password'
            #     )
            # user.logged_in = True
            # self.save(user)
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

        self.event_handler = OSFEventHandler(self.OSFFolder, self.config['dbdir'],self.user, loop=self.loop ) #create event handler
        #if config actually has legitimate data. use it.
        # if self.config != {}:
        #     self.event_handler.import_from_db(items_dict=self.config, user='himanshu', password='pass', name='himanshu', fav_movie='matrix', fav_show='simpsons')

        #start
        self.observer = Observer() #create observer. watched for events on files.
        #attach event handler to observed events. make observer recursive
        self.observer.schedule(self.event_handler, self.OSFFolder, recursive=True)
        self.observer.start() #start

    def stopObservingOSFFolder(self):
        self.observer.stop()
        self.observer.join()


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
        url = "http://osf.io/dashboard"
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
        try:
            self.storeConfigs()

            # stop polling the server
            self.stopPollingServer()

            # stop observing OSF folder
            self.stopObservingOSFFolder()
        except KeyboardInterrupt:
            print('ctr-c pressed. Still going to quit app though.')
            QApplication.instance().quit()
            raise
        except:
            print('error in tear down. Still going to quit app though.')
            QApplication.instance().quit()
            raise
        #quit the application
        QApplication.instance().quit()

    def storeConfigs(self):
        # store current configs in config file
        dir = user_config_dir(self.appname, self.appauthor)
        rel_osf_config = os.path.join(dir,'config.osf')
        file = open(rel_osf_config,'w+')
        file.truncate(0)
        file.write(json.dumps(self.config))
        file.close()

    def createConfigs(self):
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

        #new file if file doesnt exist.
        try:
            file = open(rel_osf_config,'r+w')
        except:
            file = open(rel_osf_config,'w+')

        try:

            file_content = file.read()
            self.config = json.loads(file_content)

        except ValueError:
            print('config file is corrupted. Creating new config file')
            #todo: figure out where this should actually be
            self.config={}
            self.config['appname'] = self.appname
            self.config['appauthor'] = self.appauthor
            self.config['dbdir'] = user_data_dir(self.appname, self.appauthor)
            self.storeConfigs()
        finally:
            file.close()

        print(self.config)


    def save(self, item=None):
        if item:
            self.session.add(item)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise

    # courtesy of waterbutler
    def ensure_event_loop(self):
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
