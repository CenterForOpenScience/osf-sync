__author__ = 'himanshu'
class SystemTray(QDialog):
    def __init__(self):
        super().__init__()
        self.createActions()
        self.createTrayIcon()

    def createActions(self):
        #menu items
        self.openProjectFolderAction = QAction("Open Project Folder", self)
        self.launchOSFAction = QAction("Launch OSF", self)
        self.currentlySynchingAction = QAction("Up to date", self)
        self.currentlySynchingAction.setDisabled(True)
        self.priorityAction = QAction("Priority Synching", self)
        self.preferencesAction = QAction("Preferences", self)
        self.aboutAction = QAction("&About", self)
        self.quitAction = QAction("&Quit", self)

    def createTrayIcon(self):
        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.openProjectFolderAction)
        self.trayIconMenu.addAction(self.launchOSFAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.currentlySynchingAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.priorityAction)
        self.trayIconMenu.addAction(self.preferencesAction)
        self.trayIconMenu.addAction(self.aboutAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)


        #todo: hate this icon. make better.
        icon = QIcon(':/images/cos_logo.png')
        self.trayIcon.setIcon(icon)
        self.trayIcon.show()
