from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
        QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QMenu, QPushButton, QSpinBox, QStyle, QSystemTrayIcon,
        QTextEdit, QVBoxLayout, QFileDialog, QMainWindow, QTreeWidgetItem)
from PyQt5.QtCore import QCoreApplication, Qt
from rsc.preferences_rc import Ui_Preferences # REQUIRED FOR GUI
import sys
import Item

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



    # def closeEvent(self, event):
    #     self.hide()
    #     event.ignore()
    #     self.close()

# if __name__=="__main__":
#     app = QApplication(sys.argv)
#     # QApplication.setQuitOnLastWindowClosed(False)
#     osf = Preferences("/home/himanshu/OSF-Offline/dumbdir")
#     osf.show()
#     app.exec_()




# for i in range(30):
#     # item = QTreeWidgetItem(self.preferencesWindow.treeWidget)  #top level item
#     new_item = QTreeWidgetItem(self.preferencesWindow.treeWidget.topLevelItem(0))
#     new_item.setText(0, _translate("Preferences", "{} stuff stuff".format(i)))
    # self.preferencesWindow.treeWidget.topLevelItem(0).child(i).setText(0, _translate("Preferences", "{} stuff stuff".format(i)))


# item_0 = QtWidgets.QTreeWidgetItem(self.treeWidget)
# item_1 = QtWidgets.QTreeWidgetItem(item_0)
# item_1.setCheckState(1, QtCore.Qt.Unchecked)
# item_2 = QtWidgets.QTreeWidgetItem(item_1)
# item_2.setCheckState(1, QtCore.Qt.Unchecked)
# item_3 = QtWidgets.QTreeWidgetItem(item_2)
# item_3.setCheckState(1, QtCore.Qt.Unchecked)
# item_3 = QtWidgets.QTreeWidgetItem(item_2)
# item_3.setCheckState(1, QtCore.Qt.Unchecked)

# self.preferencesWindow.treeWidget.topLevelItem(0).setText(0, _translate("Preferences", "1My Project"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(0).setText(0, _translate("Preferences", "2My other Component"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(0).child(0).setText(0, _translate("Preferences", "3folder a"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(0).child(0).child(0).setText(0, _translate("Preferences", "4New Item"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(0).child(0).child(1).setText(0, _translate("Preferences", "4folder b"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(0).child(0).child(1).child(0).setText(0, _translate("Preferences", "5some file"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(1).setText(0, _translate("Preferences", "2My Component"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(2).setText(0, _translate("Preferences", "2C component"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(2).child(0).setText(0, _translate("Preferences", "3wiki"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(2).child(1).setText(0, _translate("Preferences", "3folder"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(2).child(2).setText(0, _translate("Preferences", "3eraser"))
# self.preferencesWindow.treeWidget.topLevelItem(0).child(2).child(2).setText(0, _translate("Preferences", "hahaha it changed!"))