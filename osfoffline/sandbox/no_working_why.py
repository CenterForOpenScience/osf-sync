import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
        QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QMenu, QPushButton, QSpinBox, QStyle, QSystemTrayIcon,
        QTextEdit, QVBoxLayout, QWidget)

class Systray(QWidget):

    def __init__(self):
        super().__init__()

        self.createActions()
        self.createTrayIcon()

        self.trayIcon.show()

    def createActions(self):
        self.quitAction = QAction("&Quit", self,
            triggered=self.teardown)
    def teardown(self):
        print('torndown')
        QApplication.instance().quit()

        # self.quitAction = QtGui.QAction(self.tr("&Quit"), self)

        # QtCore.QObject.connect(self.quitAction, QtCore.SIGNAL("triggered()"),
        # QtGui.qApp, QtCore.SLOT("quit()"))



    def createTrayIcon(self):
        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)
        icon = QIcon(':/images/heart.png')
        self.trayIcon.setIcon(icon)


app = QApplication(sys.argv)
x = Systray()
sys.exit(app.exec_())