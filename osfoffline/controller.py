import os
import logging
import json
import subprocess
import webbrowser
import sys
import threading
from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog)
from PyQt5.QtCore import pyqtSignal
from appdirs import user_log_dir, user_config_dir, user_data_dir
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from osfoffline.database_manager.models import User
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save
from osfoffline.background import BackgroundWorker


"""
The various states the gui can be in:

1) not started
    application is off
    if there is data, it should be stored in db. data should be encrypted
    if there are configs, they should be stored in encrypted file.
2) started
    user starts application
    user gets to log in
    user gets to choose where to place OSF folder
3) paused (pause = not running background worker)
    stop background worker
    perform whatever actions need to be performed (eg. choose new containing folder)
4) un pause
    start background worker
5) quit (user hits quit button)
    stop background worker
    save info to config
    save info to db
    destroy gui
    stop application

state changes will be:
not started -> started ->
    pause -> resume -> pause (loop)
                            -> quit


functions that define state changes:
on_start
on_quit
on_pause
on_resume


"""


class OSFController(QDialog):

    login_signal = pyqtSignal()
    start_tray_signal = pyqtSignal()
    containing_folder_updated_signal = pyqtSignal()



    def __init__(self, app_name, app_author):
        super().__init__()
        # logging.basicConfig(level=logging.DEBUG)
        self.app_name = app_name
        self.app_author = app_author
        self.create_configs()
        self.background_worker = BackgroundWorker()




    def _can_start_background_worker(self):
        user = self.get_current_user()
        if not user.logged_in:
            return False
        if not os.path.isdir(user.osf_local_folder_path):
            return False
        if not self.background_worker:
            return False
        if self.background_worker.is_alive():
           return False

        return True






    # state functions
    def start(self):

        try:
            user = self.get_current_user()
        except MultipleResultsFound:
            self._logout_all_users()
            self.login_signal.emit()
            return
        except NoResultFound:
            self.login_signal.emit()
            return

        containing_folder = os.path.dirname(user.osf_local_folder_path)
        if not self.validate_containing_folder(containing_folder):
            self.set_containing_folder()
        user.osf_local_folder_path = os.path.join(self.containing_folder, "OSF")

        save(session, user)

        if not os.path.isdir(user.osf_local_folder_path):
            os.makedirs(user.osf_local_folder_path)

        self.start_logging()

        self.start_tray_signal.emit()
        self.background_worker.start()


    def resume(self):


        # todo: properly pause the background thread
        # I am recreating the background thread everytime for now.
        # I was unable to correctly pause the background thread
        # thus took this route for now.
        if self.background_worker is not None and self.background_worker.is_alive():
            self.background_worker.stop()
            self.background_worker.join()
        self.background_worker = BackgroundWorker()
        self.background_worker.start()


    def pause(self):

        if self.background_worker is not None and self.background_worker.is_alive():
            self.background_worker.stop()
            self.background_worker.join()




    def quit(self):
        try:
            self.store_configs()

            self.background_worker.pause_background_tasks()
            self.background_worker.stop()
            self.background_worker.join()

            session.close()

            QApplication.instance().quit()
        except Exception as e:
            logging.warning('quit broke. stopping anyways. Exception was {}'.format(e))
            # quit() stops gui and then quits application
            QApplication.instance().quit()


    def set_containing_folder_process(self):
        self.set_containing_folder()


    def _logout_all_users(self):
        for user in session.query(User):
            user.logged_in = False
            save(session, user)

    def get_current_user(self):
        return session.query(User).filter(User.logged_in).one()



    def start_logging(self):
        # make sure logging directory exists
        log_dir = user_log_dir(self.app_name, self.app_author)
        if not os.path.exists(log_dir):  # ~/.cache/appname
            os.makedirs(log_dir)


        # make sure logging file exists
        log_file = open(os.path.join(log_dir, 'osf.log'), 'w+')
        log_file.close()

        # set up config. set up format of logged info. set up "level of logging"
        # which i think is just how urgent the logging thing is. probably just a tag to each event.
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            filename=os.path.join(log_dir, 'osf.log'),
            filemode='w'
        )
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





    def validate_containing_folder(self, containing_folder):
        if not containing_folder or containing_folder == '':
            return False

        try:
            return os.path.isdir(containing_folder)
        except ValueError:
            return False

    def set_containing_folder(self):
        self.containing_folder = QFileDialog.getExistingDirectory(self, "Choose folder to place OSF folder")

    def start_osf(self):
        url = "http://osf.io/dashboard"
        webbrowser.open_new_tab(url)


    def store_configs(self):
        # store current configs in config file
        dir = user_config_dir(self.app_name, self.app_author)
        rel_osf_config = os.path.join(dir, 'config.osf')
        file = open(rel_osf_config, 'w+')
        file.truncate(0)
        file.write(json.dumps(self.config))
        file.close()


    def logout(self):
        user = self.get_current_user()
        if user:
            user.logged_in = False
            save(session, user)
            self.login_signal.emit()



    def create_configs(self):
        config_dir = self.ensure_config_dir()
        rel_osf_config = os.path.join(config_dir, 'config.osf')


        # new file if file doesnt exist.
        try:
            file = open(rel_osf_config, 'r+w')
        except:
            file = open(rel_osf_config, 'w+')

        try:
            file_content = file.read()
            self.config = json.loads(file_content)
        except ValueError:

            # todo: figure out where this should actually be
            self.config = {}
            self.config['app_name'] = self.app_name
            self.config['app_author'] = self.app_author
            self.config['db_dir'] = user_data_dir(self.app_name, self.app_author)
            self.store_configs()
        finally:
            file.close()


    def ensure_config_dir(self):
        # check if dir has config file already in it, if so use it. if not create it.
        config_dir = user_config_dir(appname=self.app_name, appauthor=self.app_author)
        # ensure directory exists
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return config_dir