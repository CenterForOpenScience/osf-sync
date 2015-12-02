import asyncio
import logging

from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QMessageBox

from sqlalchemy.orm.exc import NoResultFound

from osfoffline.database import session
from osfoffline.database.models import User
from osfoffline.exceptions import AuthError
from osfoffline.utils.authentication import AuthClient
from osfoffline.views.rsc.startscreen import Ui_startscreen


class LoginScreen(QDialog):
    """
    This class is a wrapper for the Ui_startscreen and its controls
    """

    done_logging_in_signal = pyqtSignal()
    quit_application_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_startscreen()
        self.ui.setupUi(self)
        self.ui.logInButton.clicked.connect(self.log_in)

    def exec_(self):
        try:
            # TODO Does logged_in matter?
            user = session.query(User).one()
            if user.logged_in:
                return QDialog.Accepted

            self.ui.usernameEdit.setText(user.osf_login)
            self.ui.passwordEdit.setFocus()
        except NoResultFound:
            self.ui.usernameEdit.setFocus()

        return super().exec_()

    def log_in(self):
        # self.start_screen.logInButton.setDisabled(True)  # Doesn't update until the asyncio call below returns
        logging.debug('attempting to log in')
        username = self.ui.usernameEdit.text().strip()
        password = self.ui.passwordEdit.text().strip()
        auth_client = AuthClient()
        try:
            user = session.query(User).one()
        except NoResultFound:
            user = None

        try:
            user = asyncio.get_event_loop().run_until_complete(auth_client.log_in(username=username, password=password))
        except AuthError as e:
            logging.exception(e.message)
            QMessageBox.warning(None, 'Log in Failed', e.message)
            # self.start_screen.logInButton.setEnabled(True)
        else:
            logging.info('Successfully logged in user: {}'.format(user))
            self.accept()
