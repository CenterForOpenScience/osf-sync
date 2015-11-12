import asyncio
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox

from osfoffline.database_manager.db import session
from osfoffline.database_manager.models import User
from osfoffline.exceptions import AuthError
from osfoffline.utils.authentication import AuthClient
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

    def log_in(self):
        logging.debug('attempting to log in')
        username = self.start_screen.usernameEdit.text().strip()
        password = self.start_screen.passwordEdit.text().strip()
        auth_client = AuthClient()
        try:
            user = asyncio.get_event_loop().run_until_complete(auth_client.log_in(username=username, password=password))
        except AuthError as e:
            logging.exception(e.message)
            QMessageBox.warning(
                None,
                'Log in Failed',
                e.message
            )
        else:
            logging.info('Successfully logged in user: {}'.format(user))
            self.close()

    def setup_slots(self):
        logging.debug('setting up start_screen slots')
        self.start_screen.logInButton.clicked.connect(self.log_in)

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
