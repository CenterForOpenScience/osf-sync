import json
import logging
import os
import hashlib
from decorators import can_put_stuff_in

class Item(object):
    FOLDER = 0
    FILE = 1
    PROJECT = 2
    COMPONENT = 3
    def __init__(self, kind, name, guid, path, version):
        self.kind=kind
        self.name=name
        self.guid=guid
        self.version=version
        self.items=[]
        self.path = path

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
            self.items.add_item(new_item)

    @can_put_stuff_in
    def remove_item(self, item):
        self.items.remove(item)

    @can_put_stuff_in
    def remove_item_by_name(self, item_name):
        self.items = filter(lambda i: i.name != item_name, self.items)


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
        if self==other:
            return True

    def _serialize(self, detail=True):



        if self.kind == self.FILE:
            kind = "FILE"
        elif self.kind == self.COMPONENT:
            kind = "COMPONENT"
        elif self.kind == self.FOLDER:
            kind = "FOLDER"
        elif self.kind==self.PROJECT:
            kind= "PROJECT"
        else:
            kind="UNKNOWN"

        if detail:
            self_part = {
                'kind':kind,
                'name':self.name,
                'version':self.version,
                'guid':self.guid,
                'num_items':len(self.items),
                'path':self.path,
                'items': [ i._serialize(detail) for i in self.items ]
            }
        else:
            self_part = {
                'kind':kind,
                'name':self.name,
                'items': [ i._serialize(detail) for i in self.items ]
            }


        return self_part

    def json(self):
        return json.dumps(self._serialize())

    def deserialize_item(self, item):

        return Item(
                kind=item['kind'],
                name=item['name'],
                guid=item['guid'],
                version=item['version'],
                path = item['path'],
                items=[ self._deserialize_item(i) for i in item['items']  ]
            )

















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
