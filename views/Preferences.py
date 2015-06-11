from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog, QTreeWidgetItem)
from PyQt5.QtCore import QCoreApplication, Qt

from views.rsc.preferences_rc import Ui_Preferences # REQUIRED FOR GUI

__author__ = 'himanshu'

# class Singleton(type):
#     _instances = {}
#     def __call__(cls, *args, **kwargs):
#         if cls not in cls._instances:
#             cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
#         return cls._instances[cls]


class Preferences(QDialog):
    """
    This class is a wrapper for the Ui_Preferences and its controls
    """
    GENERAL = 0
    OSF = 1
    PRIORITY = 3
    ABOUT = 4

    def __init__(self, containingFolder, treeData):
        super().__init__()
        self._translate = QCoreApplication.translate
        self.containingFolder = containingFolder
        self.treeData = treeData


    # def updateContainingFolder(self, newContainingFolder):
    #     self.containingFolder = newContainingFolder
    #     #todo: this is a hack. should make a new event, I think.
    #     self.preferencesWindow.containingFolderTextEdit.setText(self._translate("Preferences", self.containingFolder))

    def setupActions(self):
        self.setContainingFolderAction =  QAction("Set where Project will be stored", self, triggered=self.setContainingFolder)
        self.tabSelectedAction = QAction("Build Priority Tree", self, triggered=self.selector)

    def setContainingFolder(self):
        self.containingFolder = QFileDialog.getExistingDirectory(self, "Choose folder")
        #todo: this is a hack. should make a new event.
        self.preferencesWindow.containingFolderTextEdit.setText(self._translate("Preferences", self.containingFolder))


    def setupSlots(self):
        self.preferencesWindow.containingFolderTextEdit.setText(self._translate("Preferences", self.containingFolder))
        self.preferencesWindow.changeFolderButton.clicked.connect(self.setContainingFolder)
        self.preferencesWindow.tabWidget.currentChanged.connect(self.selector)

    def _createTreeFromProjectItem(self,baseTree, items):
        for item in items:
            new_tree_item = QTreeWidgetItem(baseTree)
            new_tree_item.setText(0, self._translate("Preferences", item.name))
            new_tree_item.setCheckState(1, Qt.Unchecked)
            self._createTreeFromProjectItem(new_tree_item, item.items)

    def buildPriorityTree(self, projectItem):
        self.preferencesWindow.treeWidget.clear()
        baseTree = QTreeWidgetItem(self.preferencesWindow.treeWidget)
        baseTree.setText(0,self._translate("Preferences", projectItem.name))
        self._createTreeFromProjectItem(baseTree, projectItem.items)

    def openWindow(self, tab = GENERAL):
        if self.isVisible():
            self.preferencesWindow.tabWidget.setCurrentIndex(tab)
        else:
            self.preferencesWindow = Ui_Preferences()
            self.preferencesWindow.setupUi(self)
            self.preferencesWindow.tabWidget.setCurrentIndex(tab)
            self.setupActions()
            self.setupSlots()
            self.selector(tab)
            self.show()



    def selector(self, selected_index):
        if selected_index == self.GENERAL:
            pass
        elif selected_index == self.OSF:
            pass
        elif selected_index == self.PRIORITY:
            self.buildPriorityTree(self.treeData)


