#!/usr/bin/env python



from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
        QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QMenu, QPushButton, QSpinBox, QStyle, QSystemTrayIcon,
        QTextEdit, QVBoxLayout)

import systray_rc
from appdirs import *
import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
import os
import json
import os.path





class Window(QDialog):
    def __init__(self):
        super(Window, self).__init__()


        # self.createMessageGroupBox()

        self.createActions()
        self.createTrayIcon()

        # self.showMessageButton.clicked.connect(self.showMessage)

        icon = QIcon(':/images/heart.png')
        self.trayIcon.setIcon(icon)
        # self.setWindowIcon(icon)
        self.trayIcon.messageClicked.connect(self.messageClicked)
        self.trayIcon.activated.connect(self.iconActivated)

        # mainLayout = QVBoxLayout()

        # mainLayout.addWidget(self.messageGroupBox)
        # self.setLayout(mainLayout)


        self.trayIcon.show()

        # self.setWindowTitle("Systray")
        # self.resize(400, 300)





    def setVisible(self, visible):
        self.minimizeAction.setEnabled(visible)
        self.maximizeAction.setEnabled(not self.isMaximized())
        self.restoreAction.setEnabled(self.isMaximized() or not visible)
        super(Window, self).setVisible(visible)

    def closeEvent(self, event):
        if self.trayIcon.isVisible():
            QMessageBox.information(self, "Systray",
                    "The program will keep running in the system tray. To "
                    "terminate the program, choose <b>Quit</b> in the "
                    "context menu of the system tray entry.")
            self.hide()
            event.ignore()



    def iconActivated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.iconComboBox.setCurrentIndex(
                    (self.iconComboBox.currentIndex() + 1)
                    % self.iconComboBox.count())
        elif reason == QSystemTrayIcon.MiddleClick:
            self.showMessage()

    def showMessage(self):
        icon = QSystemTrayIcon.MessageIcon(
                self.typeComboBox.itemData(self.typeComboBox.currentIndex()))
        self.trayIcon.showMessage(self.titleEdit.text(),
                self.bodyEdit.toPlainText(), icon,
                self.durationSpinBox.value() * 1000)

    def messageClicked(self):
        QMessageBox.information(None, "Systray",
                "Sorry, I already gave what help I could.\nMaybe you should "
                "try asking a human?")



    def createMessageGroupBox(self):
        self.messageGroupBox = QGroupBox("Balloon Message")

        typeLabel = QLabel("Type:")

        self.typeComboBox = QComboBox()
        self.typeComboBox.addItem("None", QSystemTrayIcon.NoIcon)
        self.typeComboBox.addItem(self.style().standardIcon(
                QStyle.SP_MessageBoxInformation), "Information",
                QSystemTrayIcon.Information)
        self.typeComboBox.addItem(self.style().standardIcon(
                QStyle.SP_MessageBoxWarning), "Warning",
                QSystemTrayIcon.Warning)
        self.typeComboBox.addItem(self.style().standardIcon(
                QStyle.SP_MessageBoxCritical), "Critical",
                QSystemTrayIcon.Critical)
        self.typeComboBox.setCurrentIndex(1)

        self.durationLabel = QLabel("Duration:")

        self.durationSpinBox = QSpinBox()
        self.durationSpinBox.setRange(5, 60)
        self.durationSpinBox.setSuffix(" s")
        self.durationSpinBox.setValue(15)

        durationWarningLabel = QLabel("(some systems might ignore this hint)")
        durationWarningLabel.setIndent(10)

        titleLabel = QLabel("Title:")

        self.titleEdit = QLineEdit("Cannot connect to network")

        bodyLabel = QLabel("Body:")

        self.bodyEdit = QTextEdit()
        self.bodyEdit.setPlainText("Don't believe me. Honestly, I don't have "
                "a clue.\nClick this balloon for details.")

        self.showMessageButton = QPushButton("Show Message")
        self.showMessageButton.setDefault(True)

        messageLayout = QGridLayout()
        messageLayout.addWidget(typeLabel, 0, 0)
        messageLayout.addWidget(self.typeComboBox, 0, 1, 1, 2)
        messageLayout.addWidget(self.durationLabel, 1, 0)
        messageLayout.addWidget(self.durationSpinBox, 1, 1)
        messageLayout.addWidget(durationWarningLabel, 1, 2, 1, 3)
        messageLayout.addWidget(titleLabel, 2, 0)
        messageLayout.addWidget(self.titleEdit, 2, 1, 1, 4)
        messageLayout.addWidget(bodyLabel, 3, 0)
        messageLayout.addWidget(self.bodyEdit, 3, 1, 2, 4)
        messageLayout.addWidget(self.showMessageButton, 5, 4)
        messageLayout.setColumnStretch(3, 1)
        messageLayout.setRowStretch(4, 1)
        self.messageGroupBox.setLayout(messageLayout)

    def createActions(self):
        # self.minimizeAction = QAction("Mi&nimize", self, triggered=self.hide)
        # self.maximizeAction = QAction("Ma&ximize", self,
        #         triggered=self.showMaximized)
        # self.restoreAction =* QAction("&Restore", self,
        #         triggered=self.showNormal)

        self.chooseSyncFolderAction = QAction("Choose Sync Folder", self, triggered=self.hide)

        self.quitAction = QAction("&Quit", self,
                triggered=self.teardown)


    def teardown(self):
        # dir = user_config_dir(appname, appauthor)
        # rel_osf_config = os.path.join(dir,'config.osf')
        # file = open(rel_osf_config,'w+')
        # file.truncate(0)
        # file.write(self.config)
        # file.close()

        QApplication.instance().quit()

    def createTrayIcon(self):
         self.trayIconMenu = QMenu(self)
         # self.trayIconMenu.addAction(self.minimizeAction)
         # self.trayIconMenu.addAction(self.maximizeAction)
         # self.trayIconMenu.addAction(self.restoreAction)
         self.trayIconMenu.addAction(self.chooseSyncFolderAction)
         self.trayIconMenu.addSeparator()
         self.trayIconMenu.addAction(self.quitAction)

         self.trayIcon = QSystemTrayIcon(self)
         self.trayIcon.setContextMenu(self.trayIconMenu)


class Item(object):
    FOLDER = 0
    FILE = 1
    def __init__(self, kind, name, guid, version=0):
        self.kind=kind
        self.name=name
        self.guid=guid
        self.version=version
        self.items=[]

    def increment_version(self):
        self.version = self.version+1

    def set_version(self, version):
        self.version = version

    #todo: checking for folder is repetitive. make decorator.
    def add_item(self, item):
        if self.kind is not self.FOLDER:
            raise TypeError
        self.items.append(item)

    def add_items(self, items):
        if self.kind is not self.FOLDER:
            raise TypeError
        self.items.extend(items)

    def remove_item(self, item):
        if self.kind is not self.FOLDER:
            raise TypeError
        self.items.remove(item)

    def remove_item_by_name(self, item_name):

        if self.kind is not self.FOLDER:
            raise TypeError
        self.items = filter(lambda i: i.name != item_name, self.items)


    def get_item_by_name(self, item_name):
        for i in self.items:
            if item_name == i.name:
                return i
        raise LookupError


    def __repr__(self):
        return json.dumps({
            'kind':'FOLDER' if self.kind==self.FOLDER else 'FILE',
            'name':self.name,
            'version':self.version,
            'guid':self.guid,
            'num_items':len(self.items)
        })

    def __str__(self):
        return json.dumps({
            'kind':'FOLDER' if self.kind==self.FOLDER else 'FILE',
            'name':self.name,
            'version':self.version,
            'guid':self.guid,
            'num_items':len(self.items)
        })

    def _serialize(self):
        self_part = {
            'kind':'FOLDER' if self.kind==self.FOLDER else 'FILE',
            'name':self.name,
            'version':self.version,
            'guid':self.guid,
            'num_items':len(self.items),
            'items': [ i._serialize() for i in self.items ]
        }

        return self_part

    def json(self):
        return json.dumps(self._serialize())






class CustomEventHandler(FileSystemEventHandler):
    """
    Base file system event handler that you can override methods from.
    """
    def __init__(self, sync_folder):
        super(CustomEventHandler, self).__init__()
        self.data = {
            'sync_folder':sync_folder
        }

    def _deserialize_item(self, item):

        return Item(
                kind=item['kind'],
                name=item['name'],
                guid=item['guid'],
                version=item['version'],
                items=[ self._deserialize_item(i) for i in item['items']  ]
            )

    # def _deserialize(self, json_string):
    #     #todo: add other config items to deserialized content
    #     return self._deserialize_item(json_string)



    def import_from_db(self, items_dict, user, password, name, fav_movie, fav_show):
        self.data['data'] = self._deserialize_item(items_dict), #todo: more complex than this because Item is object.
        self.data['user']=user
        self.data['password']=password
        self.data['name']=name
        self.data['fav_movie']=fav_movie
        self.data['fav_show']=fav_show
        #sync_folder already exists.



    def _splitpath(self,path, maxdepth=20):
        ( head, tail ) = os.path.split(path)
        return self._splitpath(head, maxdepth - 1) + [ tail ] \
            if maxdepth and head and head != path \
            else [ head or tail ]

    def _get_rel_dir(self, src_path):
        """
        if your input src_path is /home/himanshu/A/B/C/myfile AND your sync_folder is B, then
            returns B/C/myfile
        :param src_path:
        :return:
        """
        root = self.data['sync_folder']
        rel_path_without_root = os.path.relpath(src_path, root)
        root_folder_name = os.path.split(root)[1]
        return os.path.join(root_folder_name,rel_path_without_root)

    def _get_depth_arr(self, src_path):
        rel_path = self._get_rel_dir(src_path)
        return self._splitpath(rel_path)



    def _extract_name(self, src_path):
        return os.path.split(src_path)[1]


    def to_json(self):
        #todo:add metadata to json
        data = json.loads(self.data['data'].json())
        # data['user']=self.data['user']
        # data['password']=self.data['password']
        # data['name']=self.data['name']
        # data['fav_movie']=self.data['fav_movie']
        # data['fav_show']=self.data['fav_show']
        # data['sync_folder']=self.data['sync_folder']
        return json.dumps(data)




    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        what = 'directory' if event.is_directory else 'file'
        logging.info("Moved %s: from %s to %s", what, event.src_path,
                     event.dest_path)

        item_to_move_name = self._extract_name(event.src_path)
        item_to_move = [] #using array as a hack. fix.



        #get item to move. Also, remove it from current spot.
        depth_arr = self._get_depth_arr(event.src_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                item_to_move.append(cur_item.get_item_by_name(item_to_move_name))
                cur_item.remove_item_by_name(item_to_move_name)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]


        #add item to new spot.
        new_item = item_to_move[0]
        depth_arr = self._get_depth_arr(event.dest_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                cur_item.add_item(new_item)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]


        logging.info(str(self.to_json()))

    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
        what = 'directory' if event.is_directory else 'file'
        logging.info("Created %s: %s", what, event.src_path)

        if event.is_directory:
            kind = Item.FOLDER
        else:
            kind = Item.FILE

        #root dir item may not have been created yet.
        if 'data' not in self.data:
             self.data['data'] = Item(
                kind=Item.FOLDER,
                name=self._extract_name(self.data['sync_folder']),
                guid=1,
                version=0
            )

        new_item = Item(
                kind=kind,
                name=self._extract_name(event.src_path),
                guid=1,
                version=0
            )

        depth_arr = self._get_depth_arr(event.src_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                cur_item.add_item(new_item)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]

        logging.info(str(self.to_json()))






    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """
        what = 'directory' if event.is_directory else 'file'
        logging.info("Deleted %s: %s", what, event.src_path)

        item_to_remove_name = self._extract_name(event.src_path)

        # depth_arr = self._get_depth_arr(event.src_path)
        # cur_item = self.data['data']
        # while len(depth_arr) > 0:
        #     cur_item = cur_item.get_item_by_name(depth_arr[0])
        #     depth_arr = depth_arr[1:]
        #     if len(depth_arr) is 1:
        #         cur_item.remove_item_by_name(item_to_remove_name)
        #         break


        depth_arr = self._get_depth_arr(event.src_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                cur_item.remove_item_by_name(item_to_remove_name)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]

        logging.info(str(self.to_json()))



    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        logging.info("Modified %s: %s", what, event.src_path)

        item_modified_name = self._extract_name(event.src_path)

        depth_arr = self._get_depth_arr(event.src_path)


        # cur_item = self.data['data']
        # while len(depth_arr) > 0:
        #     cur_item = cur_item.get_item_by_name(depth_arr[0])
        #     depth_arr = depth_arr[1:]
        #     if len(depth_arr) is 1:
        #         cur_item.increment_version()
        #         break

        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                cur_item.increment_version()
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]

        logging.info(str(self.to_json()))



if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Systray",
                "I couldn't detect any system tray on this system.")
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    appname = "love_actually"
    appauthor = "Himanshu"

    #check if dir has config file already in it, if so use it. if not create it.


    dir = user_config_dir(appname, appauthor)
    rel_osf_config = os.path.join(dir,'config.osf')
    #ensure directory exists
    if not os.path.exists(dir):
        os.makedirs(dir)

    #new file if file doesnt exist.
    try:
        file = open(rel_osf_config,'r+w')
    except:
        file = open(rel_osf_config,'w+')
    try:

        file_content = file.read()
        config = json.loads(file_content)
    except ValueError:
        print('config file is corrupted. Creating new config file')
        config ={}
    print(config)



    #choose a folder to watch.
    sync_folder = os.path.join( os.path.dirname(os.path.realpath(__file__)), 'dumbdir')

    #if something inside the folder changes, log it to config dir
    #if something inside the folder changes, show it on console.


    #make sure logging directory exists
    log_dir = user_log_dir(appname, appauthor)
    if not os.path.exists(log_dir): # ~/.cache/appname
        os.makedirs(log_dir)
    if not os.path.exists(os.path.join(log_dir,'log')): # ~/.cache/appname/log (this is what logging uses)
        os.makedirs(os.path.join(log_dir,'log'))


    #make sure logging file exists
    log_file = open(os.path.join(log_dir,'osf.log'),'w+')
    log_file.close()

    #set up config. set up format of logged info. set up "level of logging" which i think is just how urgent the logging thing is. probably just a tag to each event.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename = os.path.join(log_dir,'osf.log'),
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)


    path = sync_folder #set this to whatever appdirs says - data_dir
    print(path)
    event_handler = CustomEventHandler(path) #create event handler
    #if config actually has legitimate data. use it.
    if config != {}:
        event_handler.import_from_db(items_dict=config, user='himanshu', password='pass', name='himanshu', fav_movie='matrix', fav_show='simpsons')

    #start
    observer = Observer() #create observer. watched for events on files.
    #attach event handler to observed events. make observer recursive
    observer.schedule(event_handler, path, recursive=True)
    observer.start() #start

    #just keeps on tracking until someone interrupts by inputting text into the console. I think.
    window = Window()
    # window.show()
    # window.config = config
    app.exec_()
    # sys.exit()
    # print('rocko')
    # try:
    #
    # except KeyboardInterrupt:
    #     observer.stop()
    #
    # observer.join() # blocks until this thread ends.



    


