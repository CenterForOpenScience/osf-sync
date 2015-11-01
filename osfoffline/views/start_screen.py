from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog)
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from PyQt5.QtCore import pyqtSignal
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save
from osfoffline.database_manager.models import User
from osfoffline.views.rsc.startscreen import Ui_startscreen  # REQUIRED FOR GUI
import logging
import furl
from requests_oauthlib import OAuth2Session
from osfoffline.utils.debug import debug_trace

__author__ = 'himanshu'
CLIENT_ID = 'eb53366f1ef347e3a7dde94cae4896be'
CLIENT_SECRET = 'iUny91itQg8hBneJZfU5yLLnvKdQfBYjdPLjvpLX'
REDIRECT_URI = 'http://localhost:5001/oauth_callback/'


API_BASE_URL = 'https://staging-api.osf.io/v2'
AUTH_BASE_URL = 'https://staging-accounts.osf.io/oauth2/authorize'
TOKEN_REQUEST_URL = 'https://staging-accounts.osf.io/oauth2/token'
TOKEN_REFRESH_URL = TOKEN_REQUEST_URL

STATE = 'RandomState'

from flask import Flask, request
app = Flask(__name__)

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/oauth_callback/', methods=['GET'])
def callback():
    """The oauth app redirects the user here; perform logic to fetch access token and redirect to a target url"""
    osf = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=STATE)
    auth_response = request.url

    # TODO: The token request fails (with CAS errors) when redirect_uri is not specified; is this a CAS bug?
    token = osf.fetch_token(TOKEN_REQUEST_URL,
                            client_secret=CLIENT_SECRET,
                            authorization_response=auth_response,
                            verify=False)

    shutdown_server()
    return token






class StartScreen(QDialog):
    """
    This class is a wrapper for the Ui_startscreen and its controls
    """

    done_logging_in_signal = pyqtSignal()
    quit_application_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.start_screen = Ui_startscreen()

    def log_user_in(self):
        base = furl.furl('http://staging-accounts.osf.io/oauth2/authorize')
        base.args['response_type'] = 'token'
        base.args['client_id'] = CLIENT_ID
        base.args['redirect_uri'] = REDIRECT_URI
        base.args['scope'] = 'user.profile'
        base.args['state'] = STATE
        base.args['access_type'] = 'offline'
        base.args['approval_prompt'] = 'force'

        import webbrowser
        webbrowser.open_new_tab(base.url)






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
            logging.warning('multiple users with same username. deleting all users with this username. restarting function.')
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