import asyncio
import concurrent
import logging

import aiohttp
import furl
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from osfoffline import settings
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save
from osfoffline.database_manager.models import User
from osfoffline.exceptions.osf_exceptions import OSFAuthError
from osfoffline.polling_osf_manager.osf_query import OSFQuery
from osfoffline.polling_osf_manager.remote_objects import RemoteUser
from osfoffline.utils.authentication import AuthClient
from osfoffline.utils.debug import debug_trace
from osfoffline.views.rsc.startscreen import Ui_startscreen


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
        logging.debug('attempting to log in')
        username = self.start_screen.usernameEdit.text().strip()
        password = self.start_screen.passwordEdit.text().strip()
        auth_client = AuthClient()
        try:
            user = yield from auth_client.log_in(username=username, password=password)
        except Exception as e:
            logging.exception(e)
            user = None

        if user:
            logging.debug('Successfully logged in user: {}'.format(user))
            self.close()
        else:
            logging.debug('Login Failed')

    def setup_slots(self):
        logging.debug('setting up start_screen slots')
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
