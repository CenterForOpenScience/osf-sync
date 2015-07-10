import json
import logging

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
