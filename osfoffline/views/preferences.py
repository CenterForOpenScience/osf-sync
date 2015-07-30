from PyQt5.QtWidgets import (QAction, QDialog, QFileDialog, QTreeWidgetItem)
from PyQt5.QtCore import QCoreApplication, QRect, Qt

from osfoffline.views.rsc.preferences_rc import Ui_Preferences  # REQUIRED FOR GUI
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save, session_scope
from osfoffline.database_manager.models import User, Node
from osfoffline.polling_osf_manager.api_url_builder import api_user_nodes
from osfoffline.polling_osf_manager.osf_query import OSFQuery
from osfoffline.polling_osf_manager.remote_objects import RemoteNode
import requests
import os
import asyncio



class Preferences(QDialog):
    """
    This class is a wrapper for the Ui_Preferences and its controls
    """
    GENERAL = 0
    OSF = 1
    ABOUT = 2

    PROJECT_NAME_COLUMN = 0
    PROJECT_SYNC_COLUMN = 1

    def __init__(self, containing_folder):
        super().__init__()
        self._translate = QCoreApplication.translate
        self.containing_folder = containing_folder
        self.preferences_window = Ui_Preferences()
        self.preferences_window.setupUi(self)
        self.preferences_closed_action = QAction("preferences window closed", self)
        self.preferences_window.changeFolderButton_2.clicked.connect(self.update_sync_nodes)
        self.tree_items = []
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

            user = session.query(User).filter(User.logged_in).one()
            containing_folder = os.path.dirname(user.osf_local_folder_path)
            self.preferences_window.containingFolderTextEdit.setText(self._translate("Preferences", containing_folder))
        elif selected_index == self.OSF:
            self.create_tree_item_for_each_top_level_node()

    def reset_tree_widget(self):
        self.tree_items.clear()
        self.preferences_window.treeWidget.clear()

    def create_tree_item_for_each_top_level_node(self):
        self.remote_top_level_nodes = self.get_remote_top_level_nodes()
        self.reset_tree_widget()
        _translate = QCoreApplication.translate


        user = session.query(User).filter(User.logged_in).one()
        for node in self.remote_top_level_nodes:
            tree_item = QTreeWidgetItem(self.preferences_window.treeWidget)
            tree_item.setCheckState(self.PROJECT_SYNC_COLUMN, Qt.Unchecked)
            tree_item.setText(self.PROJECT_NAME_COLUMN, _translate("Preferences", node.name))

            if node.id in user.guid_for_top_level_nodes_to_sync:
                tree_item.setCheckState(self.PROJECT_SYNC_COLUMN, Qt.Checked)
            self.preferences_window.treeWidget.resizeColumnToContents(self.PROJECT_NAME_COLUMN)

            self.tree_items.append(tree_item)

    def get_remote_top_level_nodes(self):
        remote_top_level_nodes = []
        try:

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
        user = session.query(User).filter(User.logged_in).one()
        guid_list = []

        for tree_item in self.tree_items:
            for name, id in [(node.name, node.id) for node in self.remote_top_level_nodes]:
                if name == tree_item.text(self.PROJECT_NAME_COLUMN):
                    if tree_item.checkState(self.PROJECT_SYNC_COLUMN) == Qt.Checked:
                        print('going to add something to list: {}'.format(id))
                        guid_list.append(id)
        print(guid_list)
        user.guid_for_top_level_nodes_to_sync = guid_list


    def closeEvent(self, event):
        print('close event called')
        if self.isVisible():
            self.hide()
            event.ignore()
            self.preferences_closed_action.trigger()