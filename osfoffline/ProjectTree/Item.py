import json
import hashlib

from osfoffline.ProjectTree.decorators import can_put_stuff_in


class Item(object):
    FOLDER = 0
    FILE = 1
    PROJECT = 2
    COMPONENT = 3
    DEFAULT_GUID = 'guid'

    def __init__(self, kind, name, guid, path, version):
        self.kind=kind
        self.name=name
        self.guid=guid
        self.version=version
        self.items=[]
        self.path = path
        self.hash = self.generate_md5()


    def increment_version(self):
        self.version = self.version+1

    def set_version(self, version):
        self.version = version

    @can_put_stuff_in
    def add_item(self, item):
        self.items.append(item)


    @can_put_stuff_in
    def add_items(self, items):
        for new_item in items:
            self.add_item(new_item)

    @can_put_stuff_in
    def remove_item(self, item):
        if not self.contains_item(item):
            raise LookupError
        self.items.remove(item)

    @can_put_stuff_in
    def remove_item_by_name(self, item_name):
        removed = False
        for item in reversed(self.items):
            if item.name == item_name:
                self.remove_item(item)
                removed=True
        if not removed:
            raise LookupError
        # self.items = filter(lambda i: i.name != item_name, self.items)

    @can_put_stuff_in
    def contains_item(self, item):
        return item in self.items

    @can_put_stuff_in
    def get_item_by_name(self, item_name):
        for i in self.items:
            if item_name == i.name:
                return i
        raise LookupError


    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()

    def __eq__(self, other):
        if self is other:
            return True
        if self.kind==other.kind and self.name==other.name and self.guid == other.guid and self.version == other.version:
            if len(self.items) != len(other.items):
                return False
            for i in self.items:
                if not other.contains_item(i):
                    return False
            for i in other.items:
                if not self.contains_item(i):
                    return False
            return True
        else:
            return False

    def serialize(self, detail=True):
        return self._serialize(detail)

    def _serialize(self, detail=True):



        # if self.kind == self.FILE:
        #     kind = "FILE"
        # elif self.kind == self.COMPONENT:
        #     kind = "COMPONENT"
        # elif self.kind == self.FOLDER:
        #     kind = "FOLDER"
        # elif self.kind==self.PROJECT:
        #     kind= "PROJECT"
        # else:
        #     kind="UNKNOWN"

        if detail:
            self_part = {
                "kind":self.kind,
                "name":self.name,
                "version":self.version,
                "guid":self.guid,
                "num_items":len(self.items),
                "path":self.path,
                "items": [ i._serialize(detail) for i in self.items ]
            }
        else:
            self_part = {
                "kind":self.kind,
                "name":self.name,
                "items": [ i._serialize(detail) for i in self.items ]
            }


        return self_part

    def json(self):
        return json.dumps(self._serialize())

    @staticmethod
    def deserialize(json_string):
        item_dict = json.loads(json_string)
        return Item._deserialize(item_dict)

    @staticmethod
    def _deserialize(item_dict):
        temp = Item(
                kind=item_dict["kind"],
                name=item_dict["name"],
                guid=item_dict["guid"],
                version=item_dict["version"],
                path = item_dict["path"],
            )
        if temp.kind is not Item.FILE:
            temp.add_items([ Item._deserialize(i) for i in item_dict["items"] ])
        return temp

    def generate_md5(self,blocksize=2**20):
        m = hashlib.md5()
        if self.kind == Item.FILE:
            with open(self.path,"rb") as f:
                while True:
                    buf = f.read(blocksize)
                    if not buf:
                        break
                    m.update(buf)
        else:
            m.update(self.json().encode())
        return m.hexdigest()



    def update_hash(self):
        self.hash = self.generate_md5()













    #
    #
    # def on_deleted(self, event):
    #     """Called when a file or directory is deleted.
    #
    #     :param event:
    #         Event representing file/directory deletion.
    #     :type event:
    #         :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
    #     """
    #     what = 'directory' if event.is_directory else 'file'
    #     logging.info("Deleted %s: %s", what, event.src_path)
    #
    #     item_to_remove_name = self._extract_name(event.src_path)
    #
    #     # depth_arr = self._get_depth_arr(event.src_path)
    #     # cur_item = self.data['data']
    #     # while len(depth_arr) > 0:
    #     #     cur_item = cur_item.get_item_by_name(depth_arr[0])
    #     #     depth_arr = depth_arr[1:]
    #     #     if len(depth_arr) is 1:
    #     #         cur_item.remove_item_by_name(item_to_remove_name)
    #     #         break
    #
    #
    #     depth_arr = self._get_depth_arr(event.src_path)
    #     cur_item = self.data['data']
    #     depth_arr = depth_arr[1:]
    #     while len(depth_arr) > 0:
    #         if len(depth_arr) is 1:
    #             cur_item.remove_item_by_name(item_to_remove_name)
    #             break
    #         cur_item = cur_item.get_item_by_name(depth_arr[0])
    #         depth_arr = depth_arr[1:]
    #
    #     logging.info(str(self.to_json()))
    #
    #
    #
    # def on_modified(self, event):
    #     """Called when a file or directory is modified.
    #
    #     :param event:
    #         Event representing file/directory modification.
    #     :type event:
    #         :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
    #     """
    #
    #     what = 'directory' if event.is_directory else 'file'
    #     logging.info("Modified %s: %s", what, event.src_path)
    #
    #     item_modified_name = self._extract_name(event.src_path)
    #
    #     depth_arr = self._get_depth_arr(event.src_path)
    #
    #
    #     # cur_item = self.data['data']
    #     # while len(depth_arr) > 0:
    #     #     cur_item = cur_item.get_item_by_name(depth_arr[0])
    #     #     depth_arr = depth_arr[1:]
    #     #     if len(depth_arr) is 1:
    #     #         cur_item.increment_version()
    #     #         break
    #
    #     cur_item = self.data['data']
    #     depth_arr = depth_arr[1:]
    #     while len(depth_arr) > 0:
    #         if len(depth_arr) is 1:
    #             cur_item.increment_version()
    #             break
    #         cur_item = cur_item.get_item_by_name(depth_arr[0])
    #         depth_arr = depth_arr[1:]
    #
    #     logging.info(str(self.to_json()))
