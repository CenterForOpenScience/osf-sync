from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog)
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from osfoffline.db import get_session, save
from osfoffline.models import User
from osfoffline.views.rsc.startscreen import Ui_startscreen  # REQUIRED FOR GUI
__author__ = 'himanshu'


class StartScreen(QDialog):
    """
    This class is a wrapper for the Ui_Preferences and its controls
    """
    GENERAL = 0
    OSF = 1
    PRIORITY = 3
    ABOUT = 4

    def __init__(self):
        super().__init__()
        self.done_logging_in_action = QAction("done logging in user", self)
        self.containing_folder = ''

        # self._translate = QCoreApplication.translate
        # self.containingFolder = containingFolder
        # self.treeData = treeData

    # def updateContainingFolder(self, newContainingFolder):
    # self.containingFolder = newContainingFolder
    #     #todo: this is a hack. should make a new event, I think.
    #     self.preferencesWindow.containingFolderTextEdit.setText(self._translate("Preferences", self.containingFolder))

    # def setupActions(self):
    #     self.setContainingFolderAction =  QAction("Set where Project will be stored", self, triggered=self.setContainingFolder)
    #     self.tabSelectedAction = QAction("Build Priority Tree", self, triggered=self.selector)

    def open_containing_folder_picker(self):
        self.containing_folder = QFileDialog.getExistingDirectory(self, "Choose folder to create OSF directory in")

    # todo: break up this function. lots of repeated code.
    def log_in(self):
        user_name = self.start_screen.emailEdit.text()  # himanshu@dayrep.com
        password = self.start_screen.passwordEdit.text()  # password
        print(user_name)
        print(password)

        # assumption: logged in user properly.
        # assumption: all the fields needed for db are set
        full_name = 'rock band'
        osf_id = 'qmjhp'
        oauth_token = 'eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLm5wb1d2bGJrb19zMXd0WEpvbXJjTkEuSzJVODIzZXFKcTgxZmNSTTNQZUZMWlAzalRqTnJGNzBEczFPc0x1bUhUN19UQ2F4ejBoSXlpNVFzM0FVZWl1N0dSV0VtbDh1TWZ5R3o1YTFjcTZSUEppZFVHbGJMcWw3QnR5SG1wRjJMUlVCM3FKZ3lQVHRqR3VpWVF1V3ZrQ2hTUEgtVk4tTW9jM3RUWlJjNXhUU0ttcDVqVm9IeG8xS29YSGI2S1YzaDdQc2tHcUVGajJ6YTdQRVlicjZrRlF0LnVGQnJRaHY2NDBGMmV0OWVjUVBqdGc.FxyoisWuhfCyVORF_qY6Umvd4p64MBcLbLWECzl_Hw5VJN93YOHQnhCdvCmFRcBbEQtZOCB-dAmiHaBBJn0RTA'

        # check if user already exists in db
        session = get_session()
        try:
            user = session.query(User).filter(User.osf_login == user_name).one()
            user.logged_in = True
            save(session, user)
            self.destroy()
            self.doneLoggingInAction.trigger()
        except MultipleResultsFound:
            # todo: multiple user screen allows you to choose which user is logged in
            print('multiple users with same username. deleting both. restarting function.')
            for user in self.session.query(User):
                if user.osf_login == user_name:
                    session.delete(user)
                    save(session)
            self.log_in()
        except NoResultFound:
            print('user doesnt exist. Creating user. and logging him in.')
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
            self.destroy()
            self.done_logging_in_action.trigger()
        session.close()

    def setup_slots(self):
        self.start_screen.logInButton.clicked.connect(self.log_in)

    def open_window(self):
        if not self.isVisible():
            self.start_screen = Ui_startscreen()
            self.start_screen.setupUi(self)
            # self.setupActions()
            self.setup_slots()
            self.show()
