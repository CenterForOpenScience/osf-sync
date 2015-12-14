import logging

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QMessageBox

from sqlalchemy.orm.exc import NoResultFound

from osfoffline.database import Session
from osfoffline.database.models import User
from osfoffline.database.utils import save
from osfoffline.exceptions import AuthError
from osfoffline.utils.authentication import AuthClient
from osfoffline.gui.qt.generated.login import Ui_login


class LoginScreen(QDialog, Ui_login):

    def __init__(self):
        super().__init__()
        self.user = None
        self.setupUi(self)
        self.logInButton.clicked.connect(self.login)

    def get_user(self):
        try:
            self.user = Session().query(User).one()
            self.user = AuthClient().populate_user_data(self.user)
            save(Session(), self.user)
            return self.user

            self.usernameEdit.setText(self.user.osf_login)
            self.passwordEdit.setFocus()
        except AuthError:
            Session().query(User).delete()
        except NoResultFound:
            self.usernameEdit.setFocus()

        self.exec_()

        if self.user:
            save(Session(), self.user)
        return self.user

    def login(self):
        # self.start_screen.logInButton.setDisabled(True)  # Doesn't update until the asyncio call below returns
        logging.debug('attempting to login')
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text().strip()
        auth_client = AuthClient()

        try:
            self.user = auth_client.login(username=username, password=password)
        except AuthError as e:
            logging.exception(e.message)
            QMessageBox.warning(None, 'Login Failed', e.message)
            # self.start_screen.logInButton.setEnabled(True)
        else:
            logging.info('Successfully logged in user: {}'.format(self.user))
            self.accept()
