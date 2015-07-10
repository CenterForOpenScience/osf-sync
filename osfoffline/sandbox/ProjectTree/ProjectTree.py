__author__ = "himanshu"
import os
from pprint import pprint

from osfoffline.ProjectTree.Item import Item


class ProjectTree(object):
    def __init__(self, path=None):
        self.project = None
        self.path = path

        if path is not None:
            self.build_from_directory(path)

    # dir input is the project folder absolute path
    def build_from_directory(self, dir):
        if not os.path.isdir(dir):
            raise NotADirectoryError
        #todo: handle folder when it ends with slash  - '/project_name/'
        # if os.path.basename(dir) =='':

        self.project = Item(
            kind=Item.PROJECT,
            name=os.path.basename(dir),
            guid=Item.DEFAULT_GUID,
            path=os.path.abspath(dir),
            version=0
        )

        self._add_items(self.project, dir)
        self.path = dir

    def build_from_serialized(self, json):
        self.project = Item.deserialize(json)

    # dir must be a full path to work on mac
    @staticmethod
    def _add_items(item, dir):

        for file_folder in os.listdir(dir):
            full_path = os.path.abspath(os.path.join(dir, file_folder))
            if os.path.isdir(full_path):
                kind = Item.FOLDER
            elif os.path.isfile(full_path):
                kind = Item.FILE
            else:
                print(file_folder)
                raise NotImplementedError
            new_item = Item(
                kind=kind,
                name=os.path.basename(file_folder),
                guid=Item.DEFAULT_GUID,
                path=full_path,
                version=0)
            item.add_item(new_item) # why is it adding on recursively????
            if os.path.isdir(full_path):
                ProjectTree._add_items(new_item, full_path)



    #todo:implement.
    def export_to_db(self):
        pass

    #todo:implement.
    def export_to_log(self):
        pass





if __name__=="__main__":
    # pt = ProjectTree()
    # import sys
    # pt.build_from_directory(sys.argv[1])
    # pprint(pt.project.serialize())
    #
    # hashes = []
    # for i in pt.project.items:
    #     # if i.kind == Item.FILE:
    #     #     print(open(i.path,"r").read())
    #     hash = pt.generate_md5(i)
    #     if hash in hashes:
    #         print("OMG, file already exists")
    #         print(open(i.path,"r").read())
    #     else:
    #         hashes.append(hash)
    DEFAULT_STRUCTURE_JSON = """{"guid": "guid",
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
             "name": "",
             "num_items": 4,
             "path": "/home/himanshu/OSF-Offline/tests/test_projects/test_project_normal",
             "version": 0}
        """
    pt = ProjectTree()
    DEFAULT_STRUCTURE = ProjectTree()

    DEFAULT_STRUCTURE.build_from_serialized(DEFAULT_STRUCTURE_JSON)

    TEST_PROJECTS_FOLDER = '/home/himanshu/OSF-Offline/tests/test_projects'
    TEST_PROJECT_NORMAL = os.path.join(TEST_PROJECTS_FOLDER,'test_project_normal')

    pt.build_from_directory(TEST_PROJECT_NORMAL)
    print('printing pt.project.serialize')
    pprint(pt.project.serialize())
    print('printing default structure.project.serialize')
    pprint(DEFAULT_STRUCTURE.project.serialize())
    # self.assertEqual(self.pt.project, self.DEFAULT_STRUCTURE.project)
