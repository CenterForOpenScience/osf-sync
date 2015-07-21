__author__ = 'himanshu'
import threading
import osfoffline.models as models
import osfoffline.polling as polling
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
import osfoffline.osf_event_handler as osf_event_handler
from watchdog.observers import Observer
from osfoffline.sync_local_filesytem_and_db import LocalDBSync
import asyncio
import osfoffline.db as db

class BackgroundWorker(threading.Thread):

    def __init__(self):
        super().__init__()
        self.session = db.get_session()
        self.user = None
        self.osf_folder = ''
        self.loop = None
        self.running = False


    def run(self):
        self.run_background_tasks()



    def run_background_tasks(self):
        print('starting run_background_tasks')
        if not self.running:
            self.loop = self.ensure_event_loop()
            self.user = self.get_current_user()
            self.osf_folder = self.user.osf_local_folder_path
            if self.user:
                self.start_observing_osf_folder()
                self.start_polling_server()
                self.running = True
                self.loop.run_forever()


    def pause_background_tasks(self):
        if self.running:
            self.stop_observing_osf_folder()
            self.stop_polling_server()
            self.stop_loop()
            self.running = False



    def start_polling_server(self):
        # todo: can probably change this to just pass in the self.user
        self.poller = polling.Poll(self.user.osf_id, self.loop)
        self.poller.start()

    def stop_polling_server(self):
        self.poller.stop()


    # todo: can refactor this code out to somewhere
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

    def stop_loop(self, close=False):
        self.loop.call_soon_threadsafe(self.loop.stop)
        if close:
            while not self.loop.is_closed():
                if not self.loop.is_running():
                    self.loop.close()

    def stop(self):
        self.stop_polling_server()
        self.stop_observing_osf_folder()
        self.stop_loop(close=True)




    def start_observing_osf_folder(self):
        # if something inside the folder changes, log it to config dir

        self.event_handler = osf_event_handler.OSFEventHandler(self.osf_folder, self.user.osf_local_folder_path, self.user,
                                                               loop=self.loop)  # create event handler
        # todo: if config actually has legitimate data. use it.
        # start
        self.observer = Observer()  # create observer. watched for events on files.
        # attach event handler to observed events. make observer recursive
        self.observer.schedule(self.event_handler, self.osf_folder, recursive=True)
        LocalDBSync(self.user.osf_local_folder_path, self.observer, self.user).emit_new_events()
        self.observer.start()  # start

    def stop_observing_osf_folder(self):
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