from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QAction)
from appdirs import user_log_dir, user_config_dir, user_data_dir
import os
from watchdog.observers import Observer
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
# from osfoffline.sync_local_filesytem_and_db import determine_new_events
import logging
import json
import subprocess
import webbrowser
import asyncio
import osf_event_handler
import polling
import models
import sys

__author__ = 'himanshu'


class OSFController(QDialog):
    def __init__(self, app_name, app_author):
        super().__init__()
        # logging.basicConfig(level=logging.DEBUG)
        self.app_name = app_name
        self.app_author = app_author

        self.containing_folder = ''

        self.login_action = QAction("Open Login Screen", self)
        self.multiple_user_action = QAction("Choose Logged In User", self)

        self.create_configs()



    def start(self):
        #todo: put this ensure_event_loop code in __init__
        self.loop = self.ensure_event_loop()

        # self.createConfigs()
        self.session = models.get_session()
        self.user = self.get_current_user()
        if self.user:
            self.containing_folder = os.path.dirname(self.user.osf_local_folder_path)
            if not self.containing_folder_is_set():
                self.set_containing_folder()
            self.user.osf_local_folder_path = os.path.join(self.containing_folder, "OSF")
            self.save(self.user)

            # todo: handle if OSF folder does not exist. OR if user wants custom OSF folder
            if not os.path.isdir(self.user.osf_local_folder_path):
                os.makedirs(self.user.osf_local_folder_path)
            self.start_logging()
            # todo: remove self.OSFFolder and replace all usages of it with self.user.osf_path
            self.osf_folder = self.user.osf_local_folder_path
            self.start_observing_osf_folder()
            # self.preferences = Preferences(self.containingFolder, self.event_handler.data['data'])
            self.start_polling_server()
            self.loop.run_forever()

    def start_polling_server(self):
        # todo: can probably change this to just pass in the self.user
        self.poller = polling.Poll(self.user.osf_id, self.loop)
        self.poller.start()

    def stop_polling_server(self):
        self.poller.stop()
        # self.poller.join()

    # todo: when log in is working, you need to make this work with log in screen.
    def get_current_user(self):
        user = None
        import threading
        print('---inside getcurrentuser-----{}----'.format(threading.current_thread()))
        try:
            user = self.session.query(models.User).filter(models.User.logged_in).one()
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
            self.multiple_user_action.trigger()
        except NoResultFound:
            # todo: allows you to log in (creates an account in db and logs it in)
            self.login_action.trigger()
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

    def start_observing_osf_folder(self):
        # if something inside the folder changes, log it to config dir
        # if something inside the folder changes, show it on console.

        self.event_handler = osf_event_handler.OSFEventHandler(self.osf_folder, self.config['db_dir'], self.user,
                                                               loop=self.loop)  # create event handler
        # todo: if config actually has legitimate data. use it.
        # start
        self.observer = Observer()  # create observer. watched for events on files.
        # attach event handler to observed events. make observer recursive
        self.observer.schedule(self.event_handler, self.osf_folder, recursive=True)
        self.observer.start()  # start

    def stop_observing_osf_folder(self):
        self.observer.stop()
        self.observer.join()

    def close_event(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()

    def open_project_folder(self):
        if self.containing_folder_is_set():
            if sys.platform == 'win32':
                os.startfile(self.containing_folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.containing_folder])
            else:
                try:
                    subprocess.Popen(['xdg-open', self.containing_folder])
                except OSError:
                    # er, think of something else to try
                    # xdg-open *should* be supported by recent Gnome, KDE, Xfce
                    pass  # todo: what to do in this case?
        else:
            self.set_containing_folder()

    def containing_folder_is_set(self):
        try:
            return os.path.isdir(self.containing_folder)
        except ValueError:
            return False

    def set_containing_folder(self, new_containing_folder=None):
        if new_containing_folder is None:
            self.containing_folder = QFileDialog.getExistingDirectory(self, "Choose folder to place OSF")
        else:
            self.containing_folder = new_containing_folder

    def start_osf(self):
        url = "http://osf.io/dashboard"
        webbrowser.open_new_tab(url)

    def currently_synching(self):
        # todo: can use this sudo code to make proper
        # if syncQueue.empty():
        #     text = "Up to date"
        # else:
        #     text = "currently {}".format(syncQueue.top().name())
        import datetime

        text = "Up to date ({})".format(str(datetime.datetime.now()))
        self.currently_synching_action.setText(0, text)

    def teardown(self):
        try:
            self.store_configs()

            # stop polling the server
            self.stop_polling_server()

            # stop observing OSF folder
            self.stop_observing_osf_folder()
        except KeyboardInterrupt:
            print('ctr-c pressed. Still going to quit app though.')
            QApplication.instance().quit()
            raise
        except:
            print('error in tear down. Still going to quit app though.')
            QApplication.instance().quit()
            raise
        # quit the application
        QApplication.instance().quit()

    def store_configs(self):
        # store current configs in config file
        dir = user_config_dir(self.app_name, self.app_author)
        rel_osf_config = os.path.join(dir, 'config.osf')
        file = open(rel_osf_config, 'w+')
        file.truncate(0)
        file.write(json.dumps(self.config))
        file.close()

    def create_configs(self):
        # todo: create helper function to check if config/data/OSF/... dirs' exist, and create them if they dont' exist.

        # check if dir has config file already in it, if so use it. if not create it.
        dir = user_config_dir(self.app_name, self.app_author)
        rel_osf_config = os.path.join(dir, 'config.osf')
        # ensure directory exists
        if not os.path.exists(dir):
            os.makedirs(dir)

        # ensure data dir exists
        data_dir = user_data_dir(self.app_name, self.app_author)

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        models.setup_db(data_dir)

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

    # todo: finish this!!!!!!!!!!
    def can_skip_startup_screen(self):
        session = models.get_session()
        try:
            session.query(models.User).filter(models.User.logged_in).one()
            return True
        except (NoResultFound, MultipleResultsFound):
            return False
