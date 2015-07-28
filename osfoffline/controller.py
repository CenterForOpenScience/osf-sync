import os
import logging
import json
import subprocess
import webbrowser
import sys

from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QAction)
from appdirs import user_log_dir, user_config_dir, user_data_dir
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

import osfoffline.database_manager.models as models
from osfoffline.database_manager.db import DB
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
    pause -> unpause -> pause (loop)
                            -> quit


functions that define state changes:
on_start
on_quit
on_pause
on_unpause


"""


class OSFController(QDialog):
    def __init__(self, app_name, app_author):
        super().__init__()
        # logging.basicConfig(level=logging.DEBUG)
        self.app_name = app_name
        self.app_author = app_author

        self.containing_folder = ''

        self.login_action = QAction("Open Login Screen", self)
        self.multiple_user_action = QAction("Choose Logged In User", self)
        self.start_tray_action = QAction("Start System Tray", self)
        self.containing_folder_updated_action = QAction("Containing Folder updated", self)

        self.create_configs()
        self.create_db()
        self.background_worker = BackgroundWorker()

    # state functions
    def start(self):
        # todo: can use session_scope here
        session = DB.get_session()
        self.user = self.get_current_user(session)

        if self.user:
            self.containing_folder = os.path.dirname(self.user.osf_local_folder_path)
            if not self.containing_folder_is_set():
                self.set_containing_folder()
            self.user.osf_local_folder_path = os.path.join(self.containing_folder, "OSF")

            save(session, self.user)

            if not os.path.isdir(self.user.osf_local_folder_path):
                os.makedirs(self.user.osf_local_folder_path)
            self.start_logging()

            self.start_tray_action.trigger()
            session.close()
            self.background_worker.start()


    def unpause(self):
        self.background_worker.run_background_tasks()


    def pause(self):
        self.background_worker.pause_background_tasks()



    def quit(self):
        try:
            import threading
            print("THREADING ON QUIT. thread is {}".format(threading.current_thread()))
            self.store_configs()
            print('HERE IS THE ISSUE?????????????????????')
            self.background_worker.pause_background_tasks()
            print('HERE IS THE ISSUE?????????????????????more????')
            self.background_worker.stop()
            print('HERE IS THE ISSUE??????????????more more more???????')
            DB.Session.remove()
        except:
            print('quit broke. stopping anyway')
            # quit() stops gui and then quits application
            QApplication.instance().quit()


    def set_containing_folder_process(self):
        self.pause()
        self.set_containing_folder()
        self.unpause()


    # todo: when log in is working, you need to make this work with log in screen.
    def get_current_user(self, session):
        user = None
        import threading
        print('---inside getcurrentuser-----{}----'.format(threading.current_thread()))
        err = False
        try:
            user = session.query(models.User).filter(models.User.logged_in).one()
        except MultipleResultsFound:
            # log out all users and restart login screen to get a single user to log in
            print('logging out all users.')
            for user in session.query(models.User):
                user.logged_in = False
                save(session, user)
            err = True
            session.close()
        except NoResultFound:
            err = True
            print('no users are logged in currently. Logging in first user in db.')
            session.close()

        if err:
            self.login_action.trigger()
        else:
            return user

    def start_logging(self):
        # make sure logging directory exists
        log_dir = user_log_dir(self.app_name, self.app_author)
        if not os.path.exists(log_dir):  # ~/.cache/appname
            os.makedirs(log_dir)
        if not os.path.exists(os.path.join(log_dir, 'log')):  # ~/.cache/appname/log (this is what logging uses)
            os.makedirs(os.path.join(log_dir, 'log'))

        # make sure logging file exists
        log_file = open(os.path.join(log_dir, 'osf.log'), 'w+')
        log_file.close()

        # set up config. set up format of logged info. set up "level of logging"
        # which i think is just how urgent the logging thing is. probably just a tag to each event.
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            filename=os.path.join(log_dir, 'osf.log'),
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


    def close_event(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()

    def open_osf_folder(self):
        if self.containing_folder_is_set():
            if sys.platform == 'win32':
                os.startfile(self.containing_folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.containing_folder])
            else:
                try:
                    subprocess.Popen(['xdg-open', self.containing_folder])
                except OSError:
                    raise NotImplementedError
        else:
            self.set_containing_folder_process()

    def containing_folder_is_set(self):
        try:
            return os.path.isdir(self.containing_folder)
        except ValueError:
            return False

    def set_containing_folder(self):
        self.containing_folder = QFileDialog.getExistingDirectory(self, "Choose folder to place OSF folder")

    def start_osf(self):
        url = "http://osf.io/dashboard"
        webbrowser.open_new_tab(url)

    # def currently_synching(self):
    #     # todo: can use this sudo code to make proper
    #     # if syncQueue.empty():
    #     #     text = "Up to date"
    #     # else:
    #     #     text = "currently {}".format(syncQueue.top().name())
    #     import datetime
    #
    #     text = "Up to date ({})".format(str(datetime.datetime.now()))
    #     self.currently_synching_action.setText(0, text)

    # def teardown(self):
    #     try:
    #         self.store_configs()
    #
    #         # stop polling the server
    #         self.background_worker.stop()
    #
    #     except KeyboardInterrupt:
    #         print('ctr-c pressed. Still going to quit app though.')
    #         QApplication.instance().quit()
    #         raise
    #     except:
    #         print('error in tear down. Still going to quit app though.')
    #         QApplication.instance().quit()
    #         raise
    #     # quit the application
    #     QApplication.instance().quit()

    def store_configs(self):
        # store current configs in config file
        dir = user_config_dir(self.app_name, self.app_author)
        rel_osf_config = os.path.join(dir, 'config.osf')
        file = open(rel_osf_config, 'w+')
        file.truncate(0)
        file.write(json.dumps(self.config))
        file.close()

    def create_db(self):
        data_dir = self.ensure_data_dir()
        DB.setup_db(data_dir)

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
            print('config file is corrupted. Creating new config file')
            # todo: figure out where this should actually be
            self.config = {}
            self.config['app_name'] = self.app_name
            self.config['app_author'] = self.app_author
            self.config['db_dir'] = user_data_dir(self.app_name, self.app_author)
            self.store_configs()
        finally:
            file.close()
        print(self.config)

    def ensure_config_dir(self):
        # check if dir has config file already in it, if so use it. if not create it.
        config_dir = user_config_dir(appname=self.app_name, appauthor=self.app_author)
        # ensure directory exists
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return config_dir

    def ensure_data_dir(self):
        # ensure data dir exists
        data_dir = user_data_dir(appname=self.app_name, appauthor=self.app_author)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir

    # todo: finish this!!!!!!!!!!
    # def can_skip_startup_screen(self):
    #     session = DB.get_session()
    #     try:
    #         session.query(models.User).filter(models.User.logged_in).one()
    #         return True
    #     except (NoResultFound, MultipleResultsFound):
    #         return False
