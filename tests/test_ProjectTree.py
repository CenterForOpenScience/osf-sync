__author__ = 'himanshu'
#for dev
import sys
sys.path.append("..")

from ProjectTree.ProjectTree import ProjectTree
from unittest import TestCase

__author__ = 'himanshu'
import os

class TestProjectTree(TestCase):

    def setUp(self):
        self.pt = ProjectTree()
        self.TEST_PROJECTS_FOLDER = 'home/himanshu/OSF-Offline/tests/test_projects/'
        self.TEST_PROJECT_NORMAL = os.path.join(self.TEST_PROJECTS_FOLDER,'test_project_normal')

        self.DEFAULT_STRUCTURE_JSON = """{"guid": "guid",
             "items": [{"guid": "guid",
                        "items": [{"guid": "guid",
                                   "items": [],
                                   "kind": "FOLDER",
                                   "name": "as",
                                   "num_items": 0,
                                   "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a/as",
                                   "version": 0},
                                  {"guid": "guid",
                                   "items": [],
                                   "kind": "FILE",
                                   "name": "b",
                                   "num_items": 0,
                                   "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a/b",
                                   "version": 0},
                                  {"guid": "guid",
                                   "items": [],
                                   "kind": "FILE",
                                   "name": "c",
                                   "num_items": 0,
                                   "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a/c",
                                   "version": 0}],
                        "kind": "FOLDER",
                        "name": "a",
                        "num_items": 3,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a",
                        "version": 0},
                       {"guid": "guid",
                        "items": [],
                        "kind": "FILE",
                        "name": "b",
                        "num_items": 0,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/b",
                        "version": 0},
                       {"guid": "guid",
                        "items": [],
                        "kind": "FILE",
                        "name": "copy1",
                        "num_items": 0,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/copy1",
                        "version": 0},
                       {"guid": "guid",
                        "items": [],
                        "kind": "FILE",
                        "name": "copy2",
                        "num_items": 0,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/copy2",
                        "version": 0}],
             "kind": "PROJECT",
             "name": "",
             "num_items": 4,
             "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal",
             "version": 0}
        """
        self.DEFAULT_STRUCTURE = ProjectTree()
        self.DEFAULT_STRUCTURE.build_from_serialized(self.DEFAULT_STRUCTURE_JSON)



    def test_build_from_directory(self):
        self.pt.build_from_directory(self.TEST_PROJECT_NORMAL)
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    """
    def test_build_from_directory_ending_with_slash(self):
        self.pt.build_from_directory()


    def test_build_from_unaccessible_directory(self):
        self.fail()
    def test_build_from_file(self):
        self.fail()
    def test_build_from_dir_with_hidden_directory(self):
        self.fail()
    def test_build_from_dir_with_hidden_file(self):
        self.fail()

    def test_build_from_dir_with_unaccessible_file(self):
        self.fail()
    def test_build_from_dir_with_unaccessible_folder(self):
        self.fail()
    def test_add_item(self):
    	self.fail()
    def test_add_items(self):
    	self.fail()
    def test_remove_item(self):
    	self.fail()
    def test_remove_items(self):
    	self.fail()
    def test_add_items_nested(self):
    	self.fail()
    def test_add_item_nested(self):
    	self.fail()

    def test_remove_item_nested(self):
    	self.fail()

    def test_remove_items_nested(self):
    	self.fail()

    def test_remove_item_by_name(self):
        self.fail()
    def test_remove_item_by_name_nested(self):
        self.fail()
    def test_remove_item_by_name(self):
        self.fail()
    def test_get_item_by_name_nested(self):
        self.fail()
    def test_get_item_by_name(self):
        self.fail()



    def test_get_from_db(self):
    	self.fail()

    def test_store_into_db(self):
    	self.fail()

    def test_get_hashes(self):
    	self.fail()

    def test_diff_files(self):
    	self.fail()

    def test_diff_files_in_diff_folders(self):
    	self.fail()

    def test_same_files_in_same_folder(self):
    	self.fail()

    def test_same_files_in_diff_folders(self):
    	self.fail()

    def test_same_files_in_diff_folders(self):
    	self.fail()
    def test_empty_project(self):
    	self.fail()

    def test_get_project_config_metada(self):
    	self.fail()

    #function tests
    def test_store_in_db_then_get_back(self):
    	self.fail()
    """

