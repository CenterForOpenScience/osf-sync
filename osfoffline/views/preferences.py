from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog)
from PyQt5.QtCore import QCoreApplication
from views.rsc.preferences_rc import Ui_Preferences  # REQUIRED FOR GUI

__author__ = 'himanshu'


class Preferences(QDialog):
    """
    This class is a wrapper for the Ui_Preferences and its controls
    """
    GENERAL = 0
    OSF = 1
    PRIORITY = 3
    ABOUT = 4

    def __init__(self, containing_folder):
        super().__init__()
        self._translate = QCoreApplication.translate
        self.containing_folder = containing_folder

    def setup_actions(self):
        self.set_containing_folder_action = QAction("Set where Project will be stored", self,
                                                    triggered=self.set_containing_folder)

    def open_containing_folder_picker(self):
        self.containing_folder = QFileDialog.getExistingDirectory(self, "Choose folder")

    def set_containing_folder(self, new_containing_folder):
        self.containing_folder = new_containing_folder
        self.preferences_window.containingFolderTextEdit.setText(self._translate("Preferences", self.containing_folder))

    def setup_slots(self):
        self.preferences_window.containingFolderTextEdit.setText(self._translate("Preferences", self.containing_folder))
        self.preferences_window.changeFolderButton.clicked.connect(self.set_containing_folder)
        self.preferences_window.tabWidget.currentChanged.connect(self.selector)

    def open_window(self, tab=GENERAL):
        if self.isVisible():
            self.preferences_window.tabWidget.setCurrentIndex(tab)
            self.selector(tab)
        else:
            self.preferences_window = Ui_Preferences()
            self.preferences_window.setupUi(self)
            self.preferences_window.tabWidget.setCurrentIndex(tab)
            self.setup_actions()
            # self.setupSlots()
            self.selector(tab)
            self.show()

    def selector(self, selected_index):
        if selected_index == self.GENERAL:
            pass
        elif selected_index == self.OSF:
            pass
        elif selected_index == self.PRIORITY:
            pass
