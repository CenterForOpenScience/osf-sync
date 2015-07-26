__author__ = 'himanshu'
from PyQt5.Qt import QIcon
from PyQt5.QtWidgets import (QDialog, QSystemTrayIcon,
                             QAction, QMenu)
import osfoffline.views.rsc.resources  # need this import for the logo to work properly.

class SystemTray(QDialog):
    def __init__(self):
        super().__init__()
        self.create_actions()
        self.create_tray_icon()

    def create_actions(self):
        # menu items
        self.open_osf_folder_action = QAction("Open OSF Folder", self)
        self.launch_osf_action = QAction("Launch OSF", self)
        self.currently_synching_action = QAction("Up to date", self)
        self.currently_synching_action.setDisabled(True)
        self.preferences_action = QAction("Preferences", self)
        self.about_action = QAction("&About", self)
        self.quit_action = QAction("&Quit", self)

    def create_tray_icon(self):
        self.tray_icon_menu = QMenu(self)
        self.tray_icon_menu.addAction(self.open_osf_folder_action)
        self.tray_icon_menu.addAction(self.launch_osf_action)
        self.tray_icon_menu.addSeparator()
        self.tray_icon_menu.addAction(self.currently_synching_action)
        self.tray_icon_menu.addSeparator()
        self.tray_icon_menu.addAction(self.preferences_action)
        self.tray_icon_menu.addAction(self.about_action)
        self.tray_icon_menu.addSeparator()
        self.tray_icon_menu.addAction(self.quit_action)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setContextMenu(self.tray_icon_menu)

        # todo: do we have a better icon for use with desktop apps?
        icon = QIcon(':/cos_logo.png')
        self.tray_icon.setIcon(icon)

    def start(self):
        self.tray_icon.show()
