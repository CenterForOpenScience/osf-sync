import logging

from PyQt5.QtWidgets import (QDialog)
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from PyQt5.QtCore import pyqtSignal
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save
from osfoffline.database_manager.models import User
from osfoffline.views.rsc.startscreen import Ui_startscreen  # REQUIRED FOR GUI


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
        user_name = self.start_screen.emailEdit.text().strip()
        password = self.start_screen.passwordEdit.text().strip()

        # assumption: logged in user properly.
        # assumption: all the fields needed for db are set
        full_name = user_name
        osf_id = user_name
        oauth_token = password
        # check if user already exists in db

        try:
            user = session.query(User).filter(User.osf_login == user_name).one()
            user.logged_in = True
            save(session, user)
            self.close()
        except MultipleResultsFound:
            logging.warning(
                'multiple users with same username. deleting all users with this username. restarting function.')
            for user in session.query(User):
                if user.osf_login == user_name:
                    session.delete(user)
                    save(session)
            self.log_in()
        except NoResultFound:
            logging.warning('user doesnt exist. Creating user. and logging them in.')
            user = User(
                full_name=full_name,
                osf_id=osf_id,
                osf_login=user_name,
                osf_local_folder_path='',
                oauth_token=oauth_token,
                osf_password=password
            )
            user.logged_in = True
            save(session, user)

            self.close()

    def setup_slots(self):
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
            # self.hide()
            # event.ignore()
            # self.destroy()
        else:
            self.quit_application_signal.emit()
        event.accept()
