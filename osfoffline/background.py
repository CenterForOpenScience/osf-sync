__author__ = 'himanshu'
import threading
import asyncio
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from watchdog.observers import Observer
import osfoffline.database_manager.models as models
import osfoffline.polling_osf_manager.polling as polling
import osfoffline.filesystem_manager.osf_event_handler as osf_event_handler
from osfoffline.database_manager.db import DB
from osfoffline.filesystem_manager.sync_local_filesytem_and_db import LocalDBSync


class BackgroundWorker(threading.Thread):

    def __init__(self):
        super().__init__()
        self.session = None
        self.user = None
        self.osf_folder = ''
        self.loop = None
        self.running = False


    def run(self):
        self.run_background_tasks()

    def run_background_tasks(self):
        print('starting run_background_tasks')
        if not self.running:
            self.session = DB.get_session()
            self.loop = self.ensure_event_loop()
            self.user = self.get_current_user()
            self.osf_folder = self.user.osf_local_folder_path
            if self.user:
                self.start_observing_osf_folder()
                self.start_polling_server()
                self.running = True
                self.loop.run_forever()

    def pause_background_tasks(self):
        print('background pause background tasks called')
        if self.running:
            print('stop polling server')
            self.stop_polling_server()
            print('stop obsering osf folder')
            self.stop_observing_osf_folder()
            print('stop loop')
            self.stop_loop()

            self.running = False

    def start_polling_server(self):
        self.poller = polling.Poll(self.user, self.loop)
        self.poller.start()

    def stop_polling_server(self):
        print('ABOUT TO STOP POLLING SERVER')
        self.poller.stop()


    # todo: can refactor this code out to somewhere
    # todo: when log in is working, you need to make this work with log in screen.
    def get_current_user(self):
        user = None
        import threading
        print('---inside getcurrentuser-----{}----'.format(threading.current_thread()))
        try:
            user = self.session.query(models.User).filter(models.User.logged_in).one()
            print('user attained in background')
        except MultipleResultsFound:
            # todo: multiple user screen allows you to choose which user is logged in

            self.multiple_user_action.trigger()
        except NoResultFound:
            self.login_action.trigger()
            print('no users are logged in currently. Logging in first user in db.')

        return user

    def stop_loop(self, close=False):
        self.loop.call_soon_threadsafe(self.loop.stop)
        if close:
            while not self.loop.is_closed():
                if not self.loop.is_running():
                    self.loop.close()

    def stop(self):
        print('background stop called')
        self.session.close()
        print('1 error')
        self.stop_polling_server()
        print('2 error')
        self.stop_observing_osf_folder()
        print('3 error')
        self.stop_loop(close=True)
        print('4 error')



    def start_observing_osf_folder(self):
        # if something inside the folder changes, log it to config dir

        self.event_handler = osf_event_handler.OSFEventHandler(self.osf_folder, self.user.osf_local_folder_path, self.user,
                                                               loop=self.loop)  # create event handler
        # todo: if config actually has legitimate data. use it.
        # start
        print('starting observer for osf folder')
        self.observer = Observer()  # create observer. watched for events on files.
        # attach event handler to observed events. make observer recursive
        print('schedule observer')
        self.observer.schedule(self.event_handler, self.osf_folder, recursive=True)
        LocalDBSync(self.user.osf_local_folder_path, self.observer, self.user).emit_new_events()

        try:
            print('observer.start')
            self.observer.start()  # start
        except OSError:
            print('too many things being watched.... hmmmm, what to dooooo????')

    def stop_observing_osf_folder(self):
        self.event_handler.close()
        self.observer.stop()
        self.observer.join()


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



"""
HOW DOES LOGIN/LOGOUT WORK?

previously logged in:
when you first open osf offline, you go to main.py which sets up views, connections, and controller.
controller sets up db, logs, and determines which user is logged in.
when all is good, controller starts background worker.
background worker polls api and observer osf folder

not logged in:
when you first open osf offline, you go to main.py which sets up views, connections, and controller.
controller sets up db, logs, and opens create user screen. user logs in. then get user from db.
when all is good, controller starts background worker.
background worker polls api and observer osf folder





"""