#usage: python -m "nose" test_ProjectTree.py
__author__ = 'himanshu'
#for dev
import sys
sys.path.append("..")

from osfoffline import ProjectTree
from osfoffline.ProjectTree import Item
from unittest import TestCase
from nose.tools import *

__author__ = 'himanshu'
import os

class TestProjectTree(TestCase):

    def printDebug(self, p1, p2):
        import pprint
        print('printing p1')
        pprint.pprint(p1.project.serialize())
        print('printing p2')
        pprint.pprint(p2.project.serialize())

    def setUp(self):
        self.pt = ProjectTree()
        self.TEST_PROJECTS_FOLDER = '/home/himanshu/OSF-Offline/tests/test_projects/'
        self.TEST_PROJECT_NORMAL = os.path.join(self.TEST_PROJECTS_FOLDER,'test_project_normal')

        self.DEFAULT_STRUCTURE_JSON = """{"guid": "guid",
             "items": [{"guid": "guid",
                        "items": [{"guid": "guid",
                                   "items": [],
                                   "kind": 0,
                                   "name": "as",
                                   "num_items": 0,
                                   "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a/as",
                                   "version": 0},
                                  {"guid": "guid",
                                   "items": [],
                                   "kind": 1,
                                   "name": "b",
                                   "num_items": 0,
                                   "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a/b",
                                   "version": 0},
                                  {"guid": "guid",
                                   "items": [],
                                   "kind": 1,
                                   "name": "c",
                                   "num_items": 0,
                                   "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a/c",
                                   "version": 0}],
                        "kind": 0,
                        "name": "a",
                        "num_items": 3,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/a",
                        "version": 0},
                       {"guid": "guid",
                        "items": [],
                        "kind": 1,
                        "name": "b",
                        "num_items": 0,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/b",
                        "version": 0},
                       {"guid": "guid",
                        "items": [],
                        "kind": 1,
                        "name": "copy1",
                        "num_items": 0,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/copy1",
                        "version": 0},
                       {"guid": "guid",
                        "items": [],
                        "kind": 1,
                        "name": "copy2",
                        "num_items": 0,
                        "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal/copy2",
                        "version": 0}],
             "kind": 2,
             "name": "test_project_normal",
             "num_items": 4,
             "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal",
             "version": 0}
        """
        self.DEFAULT_STRUCTURE = ProjectTree()
        self.DEFAULT_STRUCTURE.build_from_serialized(self.DEFAULT_STRUCTURE_JSON)



    def test_build_from_directory(self):
        self.pt.build_from_directory(self.TEST_PROJECT_NORMAL)
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    #FAILING
    # def test_build_from_directory_ending_with_slash(self):
    #     self.pt.build_from_directory(self.TEST_PROJECT_NORMAL+'/')
    #     self.printDebug(self.pt, self.DEFAULT_STRUCTURE)
    #     self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    @raises(PermissionError)
    def test_build_from_unaccessible_directory(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'test_bad_permissions_project'))

    def test_build_from_hidden_directory(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'.test_hidden_project'))
        self.DEFAULT_STRUCTURE.project.name = '.test_hidden_project'
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    @raises(NotADirectoryError)
    def test_build_from_file(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'test_project_normal','b'))
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)


    def test_build_from_dir_with_hidden_directory(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'contains_hidden_dir'))
        self.DEFAULT_STRUCTURE.project.name = 'contains_hidden_dir'
        self.DEFAULT_STRUCTURE.project.get_item_by_name('a').name = '.a'
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    def test_build_from_dir_with_hidden_file(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'contains_hidden_file'))
        self.DEFAULT_STRUCTURE.project.name = 'contains_hidden_file'
        self.DEFAULT_STRUCTURE.project.get_item_by_name('b').name = '.b'
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)



    def test_build_from_dir_with_unaccessible_file(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'contains_bad_permissions_file'))
        self.DEFAULT_STRUCTURE.project.name = 'contains_bad_permissions_file'
        # self.printDebug(self.pt, self.DEFAULT_STRUCTURE)
        self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    @raises(PermissionError)
    def test_build_from_dir_with_unaccessible_folder(self):
        self.pt.build_from_directory(os.path.join(self.TEST_PROJECTS_FOLDER,'contains_bad_permissions_folder'))
        # self.DEFAULT_STRUCTURE.project.name = 'contains_bad_permissions_folder'
        # self.DEFAULT_STRUCTURE.project.get_item_by_name('a').items = []
        # self.printDebug(self.pt, self.DEFAULT_STRUCTURE)
        # self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)

    def test_add_item(self):
        previous_item_num = len(self.DEFAULT_STRUCTURE.project.items)
        new_item_name = 'new_component'
        new_item = Item(
                kind=Item.COMPONENT,
                name=new_item_name,
                guid=Item.DEFAULT_GUID,
                version=0,
                path = os.path.join(self.DEFAULT_STRUCTURE.project.path, new_item_name)
        )
        self.DEFAULT_STRUCTURE.project.add_item(new_item)
        self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items),previous_item_num + 1)
        self.assertEqual(self.DEFAULT_STRUCTURE.project.get_item_by_name(new_item_name),new_item)



    def test_add_items(self):
        previous_item_num = len(self.DEFAULT_STRUCTURE.project.items)
        for i in range(10):
            new_item_name = 'new_component{}'.format(i)
            new_item = Item(
                    kind=Item.COMPONENT,
                    name=new_item_name,
                    guid=Item.DEFAULT_GUID,
                    version=0,
                    path = os.path.join(self.DEFAULT_STRUCTURE.project.path, new_item_name)
            )
            self.DEFAULT_STRUCTURE.project.add_item(new_item)
            self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items),previous_item_num + i+1)
            self.assertEqual(self.DEFAULT_STRUCTURE.project.get_item_by_name(new_item_name),new_item)

    def test_remove_item(self):
        previous_item_num = len(self.DEFAULT_STRUCTURE.project.items)
        item_to_remove_name = 'b'
        item_to_remove = Item(
                kind=Item.FILE,
                name=item_to_remove_name,
                guid=Item.DEFAULT_GUID,
                version=0,
                path = os.path.join(self.DEFAULT_STRUCTURE.project.path, item_to_remove_name)
        )
        self.DEFAULT_STRUCTURE.project.remove_item(item_to_remove)
        self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items), previous_item_num -1)
        self.assertRaises(LookupError, self.DEFAULT_STRUCTURE.project.get_item_by_name, item_to_remove_name)
        self.assertFalse(self.DEFAULT_STRUCTURE.project.contains_item(item_to_remove))


    # def test_remove_items(self):
    # 	self.fail()


    def test_add_items_nested(self):
        previous_item_num_in_project_top = len(self.DEFAULT_STRUCTURE.project.items)
        a_folder = self.DEFAULT_STRUCTURE.project.get_item_by_name('a')
        previous_a_folder_item_num = len(a_folder.items)
        for i in range(10):
            new_folder_name = 'new_folder{}'.format(i)
            new_folder = Item(
                    kind=Item.FOLDER,
                    name=new_folder_name,
                    guid=Item.DEFAULT_GUID,
                    version=0,
                    path = os.path.join(self.DEFAULT_STRUCTURE.project.path, new_folder_name)
            )
            new_item_name = 'new_file{}'.format(i)
            new_item = Item(
                    kind=Item.FILE,
                    name=new_item_name,
                    guid=Item.DEFAULT_GUID,
                    version=0,
                    path = os.path.join(self.DEFAULT_STRUCTURE.project.path, new_item_name)
            )
            new_folder.add_item(new_item)

            a_folder.add_item(new_folder)
            #make sure that Project level folder doesnt have changes
            self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items),previous_item_num_in_project_top)
            self.assertRaises(LookupError,self.DEFAULT_STRUCTURE.project.get_item_by_name, new_folder_name)
            #make sure that 'a' folder has changes
            self.assertEqual(len(self.DEFAULT_STRUCTURE.project.get_item_by_name('a').items),previous_a_folder_item_num + i+1)
            #note: this checks whether the new file inside the new folder was added as well.
            self.assertEqual(self.DEFAULT_STRUCTURE.project.get_item_by_name('a').get_item_by_name(new_folder_name), new_folder)


    # def test_remove_item_nested(self):
    # 	self.fail()
    #
    # def test_remove_items_nested(self):
    # 	self.fail()

    def test_remove_file_by_name(self):
        previous_item_num_in_project_top = len(self.DEFAULT_STRUCTURE.project.items)
        file_to_remove = 'b'
        self.DEFAULT_STRUCTURE.project.remove_item_by_name(file_to_remove)
        self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items),previous_item_num_in_project_top-1)
        self.assertRaises(LookupError,self.DEFAULT_STRUCTURE.project.get_item_by_name, file_to_remove)

    def test_remove_folder_by_name(self):
        previous_item_num_in_project_top = len(self.DEFAULT_STRUCTURE.project.items)
        folder_to_remove = 'a'
        self.DEFAULT_STRUCTURE.project.remove_item_by_name(folder_to_remove)
        self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items),previous_item_num_in_project_top-1)
        self.assertRaises(LookupError,self.DEFAULT_STRUCTURE.project.get_item_by_name, folder_to_remove)


    def test_remove_item_by_name_nested(self):
        """
            try and remove a file that is nested. Cant. Thus fail.
        """
        a_folder = self.DEFAULT_STRUCTURE.project.get_item_by_name('a')
        previous_item_num_in_project_top = len(self.DEFAULT_STRUCTURE.project.items)
        previous_a_folder_item_num = len(a_folder.items)
        #contained in test_project_normal/a/
        file_to_remove_name = 'c'
        file_to_remove = self.DEFAULT_STRUCTURE.project.get_item_by_name('a').get_item_by_name('c')
        #remove
        self.assertRaises(LookupError,self.DEFAULT_STRUCTURE.project.remove_item_by_name,file_to_remove_name)
        # check project folder
        self.assertEqual(len(self.DEFAULT_STRUCTURE.project.items),previous_item_num_in_project_top)
        self.assertRaises(LookupError,self.DEFAULT_STRUCTURE.project.get_item_by_name, file_to_remove_name)
        # check a folder
        self.assertEqual(len(self.DEFAULT_STRUCTURE.project.get_item_by_name('a').items),previous_a_folder_item_num)
        self.assertEqual(self.DEFAULT_STRUCTURE.project.get_item_by_name('a').get_item_by_name(file_to_remove_name), file_to_remove)




    # def test_get_item_by_name(self):
    #
    #
    # def test_get_item_by_name_nested(self):
    #     self.fail()

    def test_get_hashes(self):
        """
    	    a folder/file should have the same hash everytime you do it, unless it has changed.
    	"""
        self.assertEqual(self.DEFAULT_STRUCTURE.project.generate_md5(),self.DEFAULT_STRUCTURE.project.generate_md5())
        self.assertEqual(self.DEFAULT_STRUCTURE.project.get_item_by_name('a').generate_md5(),
                         self.DEFAULT_STRUCTURE.project.get_item_by_name('a').generate_md5())

    def test_compare_file_with_folder(self):
        self.assertNotEqual(self.DEFAULT_STRUCTURE.project.generate_md5(),self.DEFAULT_STRUCTURE.project.get_item_by_name('a').generate_md5())
        self.assertNotEqual(self.DEFAULT_STRUCTURE.project.get_item_by_name('a').generate_md5(), self.DEFAULT_STRUCTURE.project.generate_md5())

    def test_compare_file_with_diff_file(self):
        self.assertNotEqual(
            self.DEFAULT_STRUCTURE.project.get_item_by_name('b').generate_md5(),
            self.DEFAULT_STRUCTURE.project.get_item_by_name('copy1').generate_md5()
        )

    # def test_compare_file_with_diff_file_with_same_contents(self):
    #     self.assertEqual(
    #         self.DEFAULT_STRUCTURE.project.get_item_by_name('b').generate_md5(),
    #         self.DEFAULT_STRUCTURE.project.get_item_by_name('copy1').generate_md5()
    #     )

    def test_can_put_stuff_in_decorator(self):
        new_item_name = 'should not be added.'
        new_item = Item(
                    kind=Item.FILE,
                    name=new_item_name,
                    guid=Item.DEFAULT_GUID,
                    version=0,
                    path = os.path.join(self.DEFAULT_STRUCTURE.project.path, new_item_name)
            )
        self.assertRaises(TypeError, self.DEFAULT_STRUCTURE.project.get_item_by_name('b').add_item,new_item )
        self.assertRaises(TypeError, self.DEFAULT_STRUCTURE.project.get_item_by_name('copy1').add_item,new_item)
        self.assertRaises(TypeError, self.DEFAULT_STRUCTURE.project.get_item_by_name('a').get_item_by_name('b').add_item,new_item)



    """
    def test_get_from_db(self):
    	self.fail()

    def test_store_into_db(self):
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



