from PyQt5.QtCore import QObject, pyqtSignal,pyqtSlot
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
        QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QMenu, QPushButton, QSpinBox, QStyle, QSystemTrayIcon,
        QTextEdit, QVBoxLayout, QFileDialog, QMainWindow)
from rsc.preferences_rc import Ui_Preferences
import sys

class Controller(QDialog):
    trigger = pyqtSignal()
    def __init__(self):
        super().__init__()
        # Define a new signal called 'trigger' that has no arguments.

        preferencesWindow = Ui_Preferences()
        preferencesWindow.setupUi(self)
        self.show()

        self.view = View()

    def connect_and_emit_trigger(self):
        # # Connect the trigger signal to a slot.
        # self.trigger.connect(self.handle_trigger)
        #
        # # Emit the signal.
        # self.trigger.emit()

        self.act = QAction("bar", self, triggered=self.view.handle_trigger)
        self.act.trigger()
        #act = QAction(NAME OF SLOT TO CONNECT TO, self, TYPE OF TRIGGER=SLOT?)

    def handle_trigger(self):
        # Show that the slot has been called.

        print("trigger signal received1111")

class View(QObject):


    # Define a new signal called 'trigger' that has no arguments.
    trigger = pyqtSignal()

    def connect_and_emit_trigger(self):
        # Connect the trigger signal to a slot.
        # self.trigger.connect(self.handle_trigger)

        # Emit the signal.
        # self.trigger.emit()

        self.containingFolderChanged = pyqtSignal(str, name='containingFolderChanged')
        self.containingFolderChanged.connect(self)
        # self.containingFolderChanged.emit(self.)


    @pyqtSlot(name='bar')
    def handle_trigger(self):
        # Show that the slot has been called.

        print("dude, bar was called!")

from PyQt5.QtWidgets import QComboBox

class Bar(QComboBox):

    def connect_activated(self):
        # The PyQt5 documentation will define what the default overload is.
        # In this case it is the overload with the single integer argument.
        self.activated.connect(self.handle_int)

        # For non-default overloads we have to specify which we want to
        # connect.  In this case the one with the single string argument.
        # (Note that we could also explicitly specify the default if we
        # wanted to.)
        self.activated[str].connect(self.handle_string)

    def handle_int(self, index):
        print( "activated signal passed integer", index)

    def handle_string(self, text):
        print("activated signal passed QString", text)




class Controller2(QDialog):

    trigger1 = pyqtSignal()

    def __init__(self):
        super().__init__()


    def stuff_happened(self):
        self.trigger1.emit()

    def updateFolder(self, newfolder):
        print("controller changed folder as well. new folder is {}".format(newfolder))

class View2(QDialog):

    folderChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.preferencesWindow = Ui_Preferences()
        self.preferencesWindow.setupUi(self)
        self.show()

    def my_slot(self):
        print('haha my slot called.')

    def folderChangeDialog(self):
        newfolder = QFileDialog.getExistingDirectory(self, "Choose folder")
        self.folderChanged.emit(newfolder)



    def changeEditTextValue(self, newText):
        self.preferencesWindow.containingFolderTextEdit.setText(self._translate("Preferences", self.containingFolder))

    def updateFolder(self, newFolder):
        print("folder can be updated in view now. new folder will be {}".format(newFolder))


class App2(QDialog):
    def __init__(self):
        super().__init__()
        self.controller = Controller2()
        self.view = View2()
        self.setupConnections()

    def setupConnections(self):
        self.connectSignalSlot(self.controller.trigger1, self.view.my_slot)
        self.connectSignalSlot(signal = self.view.preferencesWindow.changeFolderButton.clicked,
                               slot = self.view.folderChangeDialog
                               )
        self.connectSignalSlot(signal=self.view.folderChanged,
                               slot =  self.view.updateFolder
                               )
        self.connectSignalSlot(signal=self.view.folderChanged,
                               slot =  self.controller.updateFolder
                               )






    def connectSignalSlot(self, signal, slot):
        signal.connect(slot)




if __name__=="__main__":
    app = QApplication(sys.argv)
    # foo = Controller()
    # foo.connect_and_emit_trigger()

    osf = App2()




    view = View()
    app.exec_()
    foo = Controller()

