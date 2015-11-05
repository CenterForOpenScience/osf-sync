import furl
import aiohttp
import asyncio
import logging
import concurrent
from flask import request

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from osfoffline import settings
from osfoffline.utils.debug import debug_trace
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save
from osfoffline.database_manager.models import User
from osfoffline.views.rsc.startscreen import Ui_startscreen
from osfoffline.exceptions.osf_exceptions import OSFAuthError
from osfoffline.polling_osf_manager.osf_query import OSFQuery


class StartScreen(QDialog):
    """
    This class is a wrapper for the Ui_startscreen and its controls
    """

    done_logging_in_signal = pyqtSignal()
    quit_application_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.start_screen = Ui_startscreen()

    @asyncio.coroutine
    def log_in(self):
        logging.info('attempting to log in')
        personal_access_token = self.start_screen.personalAccessTokenEdit.text().strip()
        url = settings.API_BASE + '/v2/users/me/'
        loop = asyncio.get_event_loop()
        osf = OSFQuery(loop, personal_access_token)
        logging.info('url: {}'.format(url))
        try:
            resp = yield from osf.make_request(url)
        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, concurrent.futures._base.TimeoutError):
            # No internet connection
            # TODO: Pretend user has logged in and retry when connection has been established
            raise

        if resp.status == 200:
            json_resp = yield from resp.json()
            full_name = json_resp['data']['attributes']['full_name']     # Use one of these later to "Welcome {user}"
            given_name = json_resp['data']['attributes']['given_name']   # Use one of these later to "Welcome {user}"
            osf_id = json_resp['data']['id']

            try:
                user = session.query(User).filter(User.osf_login == osf_id).one()
                user.logged_in = True
                save(session, user)
                self.close()
            except MultipleResultsFound:
                logging.warning('multiple users with same username. deleting all users with this username. restarting function.')
                for user in session.query(User):
                    if user.osf_login == osf_id:
                        session.delete(user)
                        save(session)
                self.log_in()
            except NoResultFound:
                logging.warning('user doesnt exist. Creating user. and logging them in.')
                user = User(
                    full_name=full_name,
                    osf_id=osf_id,
                    osf_login='',  # TODO: email goes here when more auth methods are added, not currently returned by APIv2
                    osf_local_folder_path='',
                    oauth_token=personal_access_token,
                )
                user.logged_in = True
                save(session, user)

        else:
            # Authentication failed, user has likely provided an invalid token
            raise OSFAuthError('Invalid auth response: {}'.format(resp.status))

        self.close()

    def setup_slots(self):
        logging.info('setting up start_screen slots')
        self.start_screen.logInButton.clicked.connect(lambda: asyncio.get_event_loop().run_until_complete(self.log_in()))

    def open_window(self):
        if not self.isVisible():
            self.start_screen.setupUi(self)
            self.setup_slots()
            self.show()

    def _user_logged_in(self):
        try:
            session.query(User).filter(User.logged_in).one()
            return True
        except:
            return False

    def closeEvent(self, event):
        """ If closeEvent occured by us, then it means user is properly logged in. Thus close.
            Else, event is by user without logging in. THUS, quit entire application.
        """
        if self._user_logged_in():
            self.done_logging_in_signal.emit()
        else:
            self.quit_application_signal.emit()
        event.accept()
