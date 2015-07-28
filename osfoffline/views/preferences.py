from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog, QTreeWidgetItem)
from PyQt5.QtCore import QCoreApplication, QRect, Qt

from osfoffline.views.rsc.preferences_rc import Ui_Preferences  # REQUIRED FOR GUI
from osfoffline.database_manager.db import DB
from osfoffline.database_manager.utils import save
from osfoffline.database_manager.models import User, Node
from osfoffline.polling_osf_manager.api_url_builder import api_user_nodes
from osfoffline.polling_osf_manager.osf_query import OSFQuery
from osfoffline.polling_osf_manager.remote_objects import RemoteNode
import requests

import asyncio
__author__ = 'himanshu'


class Preferences(QDialog):
    """
    This class is a wrapper for the Ui_Preferences and its controls
    """
    GENERAL = 0
    OSF = 1
    ABOUT = 4

    def __init__(self, containing_folder):
        super().__init__()
        self._translate = QCoreApplication.translate
        self.containing_folder = containing_folder
        self.preferences_window = Ui_Preferences()
        self.preferences_window.setupUi(self)
        self.preferences_closed_action = QAction("preferences window closed", self)
        self.preferences_window.changeFolderButton_2.clicked.connect(self.update_sync_nodes)
        self.check_boxes = []
        self.setup_slots()

    def setup_actions(self):
        self.set_containing_folder_action = QAction("Set where Project will be stored", self,
                                                    triggered=self.set_containing_folder)

    def open_containing_folder_picker(self):
        self.containing_folder = QFileDialog.getExistingDirectory(self, "Choose where to place OSF folder")

    def set_containing_folder(self, new_containing_folder):
        print('is this function called!!!!!!!')
        self.containing_folder = new_containing_folder
        self.preferences_window.containingFolderTextEdit.setText(self._translate("Preferences", self.containing_folder))

    def update_containing_folder_text(self, containing_folder):
        print('update containing folder text in preferences called')
        print('above was called with the argument containing_folder={}'.format(containing_folder))
        self.containing_folder = containing_folder
        self.preferences_window.containingFolderTextEdit.setText(self._translate("Preferences", self.containing_folder))


    def setup_slots(self):
        # self.preferences_window.containingFolderTextEdit.setText(self._translate("Preferences", self.containing_folder))
        # self.preferences_window.changeFolderButton.clicked.connect(self.set_containing_folder)
        self.preferences_window.tabWidget.currentChanged.connect(self.selector)

    def open_window(self, tab=GENERAL):
        if self.isVisible():
            self.preferences_window.tabWidget.setCurrentIndex(tab)
            self.selector(tab)
        else:
            self.preferences_window.tabWidget.setCurrentIndex(tab)
            self.setup_actions()
            # self.setupSlots()
            self.selector(tab)
            self.show()

    def selector(self, selected_index):
        if selected_index == self.GENERAL:
            pass
        elif selected_index == self.OSF:
            self.create_checkbox_for_each_top_level_node()

    def reset_tree_widget(self):
        self.check_boxes.clear()
        self.preferences_window.treeWidget.clear()

    def create_checkbox_for_each_top_level_node(self):
        self.remote_top_level_nodes = self.get_remote_top_level_nodes()
        self.reset_tree_widget()
        _translate = QCoreApplication.translate
        # y_from_top = 0
        # height = 22
        for node in self.remote_top_level_nodes:
            check_box = QTreeWidgetItem(self.preferences_window.treeWidget)
            check_box.setCheckState(1, Qt.Unchecked)
            check_box.setText(0, _translate("Preferences", node.name))
            # new_checkbox = QCheckBox(self.preferences_window.scrollAreaWidgetContents)
            # new_checkbox.setGeometry(QRect(30, y_from_top, 97, height))
            # y_from_top += height+5
            # new_checkbox.setObjectName(node.name)
            # new_checkbox.setText(_translate("Preferences", node.name))
            session = DB.get_session()
            user = session.query(User).filter(User.logged_in).one()
            if node.id in user.guid_for_top_level_nodes_to_sync:
                check_box.setCheckState(1, Qt.Checked)
            self.preferences_window.treeWidget.resizeColumnToContents(0)
            session.close()
            self.check_boxes.append(check_box)

    def get_remote_top_level_nodes(self):
        remote_top_level_nodes = []
        try:
            session = DB.get_session()
            user = session.query(User).filter(User.logged_in).one()
            if user:
                user_nodes = []
                url = api_user_nodes(user.osf_id)
                headers={'Authorization': 'Bearer {}'.format(user.oauth_token)}
                resp = requests.get(url, headers=headers).json()
                user_nodes.extend(resp['data'])
                while resp['links']['next']:
                    resp = requests.get(resp['links']['next'], headers=headers).json()
                    user_nodes.extend(resp['data'])
                for node in user_nodes:
                    verified_node = RemoteNode(node)
                    if verified_node.is_top_level:
                        remote_top_level_nodes.append(verified_node)
        except Exception as e:
            print(e)
        return remote_top_level_nodes

    def update_sync_nodes(self):
        session = DB.get_session()
        user = session.query(User).filter(User.logged_in).one()
        guid_list = []

        for checkbox in self.check_boxes:
            for name, id in [(node.name, node.id) for node in self.remote_top_level_nodes]:
                if name == checkbox.text(0):
                    if checkbox.checkState(1) == Qt.Checked:
                        print('going to add something to list: {}'.format(id))
                        guid_list.append(id)
        print(guid_list)
        user.guid_for_top_level_nodes_to_sync = guid_list
        save(session, user)
        session.close()

