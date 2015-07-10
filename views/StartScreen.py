from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog, QTreeWidgetItem)
from PyQt5.QtCore import QCoreApplication, Qt
from models import get_session, User, save
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from views.rsc.startscreen import Ui_startscreen # REQUIRED FOR GUI

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
        self.doneLoggingInAction = QAction("done logging in user", self)

        # self._translate = QCoreApplication.translate
        # self.containingFolder = containingFolder
        # self.treeData = treeData


    # def updateContainingFolder(self, newContainingFolder):
    #     self.containingFolder = newContainingFolder
    #     #todo: this is a hack. should make a new event, I think.
    #     self.preferencesWindow.containingFolderTextEdit.setText(self._translate("Preferences", self.containingFolder))

    # def setupActions(self):
    #     self.setContainingFolderAction =  QAction("Set where Project will be stored", self, triggered=self.setContainingFolder)
    #     self.tabSelectedAction = QAction("Build Priority Tree", self, triggered=self.selector)

    def openContainingFolderPicker(self):
        self.containingFolder = QFileDialog.getExistingDirectory(self, "Choose folder to create OSF directory in")

    #todo: break up this function. lots of repeated code.
    def logIn(self):
        username = self.startScreen.emailEdit.text()
        password = self.startScreen.passwordEdit.text()
        print(username)
        print(password)

        # assumption: logged in user properly.
        #assumption: all the fields needed for db are set
        fullname = 'Johnny Appleseed'
        osf_id = '3672r'
        oauth_token ='eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ'


        #check if user already exists in db
        session = get_session()
        try:
            user = session.query(User).filter(User.osf_login == username).one()
            user.logged_in = True
            save(session,user)
            self.destroy()
            self.doneLoggingInAction.trigger()
        except MultipleResultsFound:
            # todo: multiple user screen allows you to choose which user is logged in
            print('multiple users with same username. deleting both. restarting function.')
            for user in self.session.query(User):
                if user.osf_login == username:
                    session.delete(user)
                    save(session)
            self.logIn()
        except NoResultFound:
            print('user doesnt exist. Creating user. and logging him in.')
            user = User(
                fullname = fullname,
                osf_id=osf_id,
                osf_login = username,
                osf_path= '',
                oauth_token=oauth_token,
                osf_password=password
            )
            user.logged_in = True
            save(session,user)
            self.destroy()
            self.doneLoggingInAction.trigger()
        session.close()



    def setupSlots(self):
        self.startScreen.logInButton.clicked.connect(self.logIn)


    def openWindow(self):
        if not self.isVisible():
            self.startScreen = Ui_startscreen()
            self.startScreen.setupUi(self)
            # self.setupActions()
            self.setupSlots()
            self.show()



