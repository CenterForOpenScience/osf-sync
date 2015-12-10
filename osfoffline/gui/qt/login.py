import asyncio
import logging

from PyQt5.QtWidgets import QDialog, QInputDialog, QMessageBox

from sqlalchemy.orm.exc import NoResultFound

from osfoffline.database import session
from osfoffline.database.models import User
from osfoffline.database.utils import save
from osfoffline.exceptions import AuthError, TwoFactorRequiredError
from osfoffline.utils.authentication import AuthClient
from osfoffline.gui.qt.generated.login import Ui_login


logger = logging.getLogger(__name__)


class LoginScreen(QDialog, Ui_login):

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

    def log_in(self, *, otp=None):
        # self.start_screen.logInButton.setDisabled(True)  # Doesn't update until the asyncio call below returns
        logger.debug('attempting to log in')
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text().strip()
        auth_client = AuthClient()

        try:
            self.user = asyncio.get_event_loop().run_until_complete(
                auth_client.log_in(username=username, password=password, otp=otp))
        except TwoFactorRequiredError:
            # Prompt user for 2FA code, then re-try authentication
            otp_val, ok = QInputDialog.getText(self, 'Enter one-time code',
                                               'Please enter a two-factor authentication code.\n'
                                               '(check your mobile device)')
            if ok:
                return self.log_in(otp=otp_val)
        except AuthError as e:
            logger.exception(e.message)
            QMessageBox.warning(None, 'Log in Failed', e.message)
            # self.start_screen.logInButton.setEnabled(True)
        else:
            logger.info('Successfully logged in user: {}'.format(self.user))
            self.accept()
