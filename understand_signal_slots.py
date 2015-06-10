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
        self.trigger.connect(self.handle_trigger)

        # Emit the signal.
        self.trigger.emit()

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


if __name__=="__main__":
    app = QApplication(sys.argv)
    foo = Controller()
    foo.connect_and_emit_trigger()
    # view = View()
    app.exec_()
    foo = Controller()

