__author__ = 'himanshu'
import os
from Item import Item
from pprint import pprint

class ProjectTree(object):
    def __init__(self):
        self.project = None

    #dir input is the project folder absolute path
    def build_from_directory(self, dir):
        if not os.path.isdir(dir):
            raise NotADirectoryError
        self.project = Item(Item.PROJECT,os.path.dirname(dir) , 'guid', version=0)

        self._add_items(self.project, dir )



    #dir must be a full path to work on mac
    def _add_items(self, item, dir):
        for file_folder in os.listdir(dir):

            if os.path.isdir(os.path.join(dir,file_folder)):
                kind = Item.FOLDER
            elif os.path.isfile(os.path.join(dir,file_folder)):
                kind = Item.FILE
            else:
                print(file_folder)
                raise NotImplementedError
            new_item = Item(kind, os.path.basename(file_folder), 'guid',version=0)
            item.add_item(new_item)
            if os.path.isdir(file_folder):
                self._add_items(new_item, file_folder)


if __name__=="__main__":
    pt = ProjectTree()
    import sys
    pt.build_from_directory(sys.argv[1])
    pprint(pt.project)