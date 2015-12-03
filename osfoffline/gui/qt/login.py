import asyncio
import logging

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QMessageBox

from sqlalchemy.orm.exc import NoResultFound

from osfoffline.database import session
from osfoffline.database.models import User
from osfoffline.database.utils import save
from osfoffline.exceptions import AuthError
from osfoffline.utils.authentication import AuthClient
from osfoffline.views.rsc.startscreen import Ui_startscreen


class LoginScreen(QDialog, Ui_startscreen):
    """
    This class is a wrapper for the Ui_startscreen and its controls
    """

    def __init__(self):
        super().__init__()
        self.user = None
        self.setupUi(self)
        self.logInButton.clicked.connect(self.log_in)

    def get_user(self):
        try:
            self.user = session.query(User).one()
            self.user = asyncio.get_event_loop().run_until_complete(AuthClient().populate_user_data(self.user))
            save(session, self.user)
            return self.user

            self.usernameEdit.setText(self.user.osf_login)
            self.passwordEdit.setFocus()
        except AuthError:
            session.query(User).delete()
        except NoResultFound:
            self.usernameEdit.setFocus()

        self.exec_()

        if self.user:
            save(session, self.user)
        return self.user

    def log_in(self):
        # self.start_screen.logInButton.setDisabled(True)  # Doesn't update until the asyncio call below returns
        logging.debug('attempting to log in')
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text().strip()
        auth_client = AuthClient()

        try:
            self.user = asyncio.get_event_loop().run_until_complete(auth_client.log_in(username=username, password=password))
        except AuthError as e:
            logging.exception(e.message)
            QMessageBox.warning(None, 'Log in Failed', e.message)
            # self.start_screen.logInButton.setEnabled(True)
        else:
            logging.info('Successfully logged in user: {}'.format(self.user))
            self.accept()
