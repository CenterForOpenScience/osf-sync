from watchdog.events import LoggingEventHandler, FileSystemEventHandler
import os
import json
import logging
from Item import Item
class CustomEventHandler(FileSystemEventHandler):
    """
    Base file system event handler that you can override methods from.
    """
    def __init__(self, sync_folder):
        super(CustomEventHandler, self).__init__()
        self.data = {
            'sync_folder':sync_folder
        }

    def _deserialize_item(self, item):

        return Item(
                kind=item['kind'],
                name=item['name'],
                guid=item['guid'],
                version=item['version'],
                items=[ self._deserialize_item(i) for i in item['items']  ]
            )

    # def _deserialize(self, json_string):
    #     #todo: add other config items to deserialized content
    #     return self._deserialize_item(json_string)



    def import_from_db(self, items_dict, user, password, name, fav_movie, fav_show):
        self.data['data'] = self._deserialize_item(items_dict), #todo: more complex than this because Item is object.
        self.data['user']=user
        self.data['password']=password
        self.data['name']=name
        self.data['fav_movie']=fav_movie
        self.data['fav_show']=fav_show
        #sync_folder already exists.



    def _splitpath(self,path, maxdepth=20):
        ( head, tail ) = os.path.split(path)
        return self._splitpath(head, maxdepth - 1) + [ tail ] \
            if maxdepth and head and head != path \
            else [ head or tail ]

    def _get_rel_dir(self, src_path):
        """
        if your input src_path is /home/himanshu/A/B/C/myfile AND your sync_folder is B, then
            returns B/C/myfile
        :param src_path:
        :return:
        """
        root = self.data['sync_folder']
        rel_path_without_root = os.path.relpath(src_path, root)
        root_folder_name = os.path.split(root)[1]
        return os.path.join(root_folder_name,rel_path_without_root)

    def _get_depth_arr(self, src_path):
        rel_path = self._get_rel_dir(src_path)
        return self._splitpath(rel_path)



    def _extract_name(self, src_path):
        return os.path.split(src_path)[1]


    def to_json(self):
        #todo:add metadata to json
        data = json.loads(self.data['data'].json())
        # data['user']=self.data['user']
        # data['password']=self.data['password']
        # data['name']=self.data['name']
        # data['fav_movie']=self.data['fav_movie']
        # data['fav_show']=self.data['fav_show']
        # data['sync_folder']=self.data['sync_folder']
        return json.dumps(data)




    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        what = 'directory' if event.is_directory else 'file'
        logging.info("Moved %s: from %s to %s", what, event.src_path,
                     event.dest_path)

        item_to_move_name = self._extract_name(event.src_path)
        item_to_move = [] #using array as a hack. fix.



        #get item to move. Also, remove it from current spot.
        depth_arr = self._get_depth_arr(event.src_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                item_to_move.append(cur_item.get_item_by_name(item_to_move_name))
                cur_item.remove_item_by_name(item_to_move_name)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]


        #add item to new spot.
        new_item = item_to_move[0]
        depth_arr = self._get_depth_arr(event.dest_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                cur_item.add_item(new_item)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]


        logging.info(str(self.to_json()))

    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
        what = 'directory' if event.is_directory else 'file'
        logging.info("Created %s: %s", what, event.src_path)

        if event.is_directory:
            kind = Item.FOLDER
        else:
            kind = Item.FILE

        #root dir item may not have been created yet.
        if 'data' not in self.data:
             self.data['data'] = Item(
                kind=Item.FOLDER,
                name=self._extract_name(self.data['sync_folder']),
                guid=1,
                version=0
            )

        new_item = Item(
                kind=kind,
                name=self._extract_name(event.src_path),
                guid=1,
                version=0
            )

        depth_arr = self._get_depth_arr(event.src_path)
        cur_item = self.data['data']
        depth_arr = depth_arr[1:]
        while len(depth_arr) > 0:
            if len(depth_arr) is 1:
                cur_item.add_item(new_item)
                break
            cur_item = cur_item.get_item_by_name(depth_arr[0])
            depth_arr = depth_arr[1:]

        logging.info(str(self.to_json()))
