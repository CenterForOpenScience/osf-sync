__author__ = 'himanshu'
import os
from Item import Item
from pprint import pprint
import hashlib

class ProjectTree(object):
    def __init__(self, project=None, path='.'):
        self.project = project
        self.path = path

    # dir input is the project folder absolute path
    def build_from_directory(self, dir):
        if not os.path.isdir(dir):
            raise NotADirectoryError
        self.project = Item(
            kind=Item.PROJECT,
            name=os.path.basename(dir) ,
            guid='guid',
            path=os.path.abspath(dir),
            version=0
        )
        self._add_items(self.project, dir)
        self.path = dir

    def build_from_serialized(self, json):
        self.project = Item.deserialize_item(json)

    # dir must be a full path to work on mac
    def _add_items(self, item, dir):
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
                guid='guid',
                path=full_path,
                version=0)
            item.add_item(new_item)
            if os.path.isdir(full_path):
                self._add_items(new_item, full_path)

    def generate_md5(self,item,blocksize=2**20):
        m = hashlib.md5()
        if item.kind == Item.FILE:
            with open(item.path,"rb") as f:
                while True:
                    buf = f.read(blocksize)
                    if not buf:
                        break
                    m.update(buf)
        else:
            m.update(item.json().encode())
        return m.hexdigest()

    #todo:implement.
    def export_to_db(self):
        pass

    #todo:implement.
    def export_to_log(self):
        pass





if __name__=="__main__":
    pt = ProjectTree()
    import sys
    pt.build_from_directory(sys.argv[1])
    pprint(pt.project._serialize())

    hashes = []
    for i in pt.project.items:
        # if i.kind == Item.FILE:
        #     print(open(i.path,'r').read())
        hash = pt.generate_md5(i)
        if hash in hashes:
            print("OMG, file already exists")
            print(open(i.path,'r').read())
        else:
            hashes.append(hash)