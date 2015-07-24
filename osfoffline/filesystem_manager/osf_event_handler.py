"""
This is the most important file in the system. OSFEventHandler is responsible for updating the models,
storing the data into the db, and then sending a request to the remote server.
"""
import asyncio

from watchdog.events import FileSystemEventHandler

from osfoffline.database_manager.models import Node, File
from osfoffline.database_manager.db import get_session, save
from osfoffline.utils.path import ProperPath
from osfoffline.exceptions.event_handler_exceptions import MovedNodeUnderFile

EVENT_TYPE_MOVED = 'moved'
EVENT_TYPE_DELETED = 'deleted'
EVENT_TYPE_CREATED = 'created'
EVENT_TYPE_MODIFIED = 'modified'


def console_log(variable_name, variable_value):
    print("DEBUG: {}: {}".format(variable_name, variable_value))


class OSFEventHandler(FileSystemEventHandler):
    """
    Base file system event handler that you can override methods from.
    """

    def __init__(self, osf_folder, db_url, user, loop):
        super().__init__()
        self._loop = loop or asyncio.get_event_loop()
        self.osf_folder = osf_folder

        self.session = get_session()
        self.user = user

        print('osf event handler created')


    def close(self):
        save(self.session)
        self.session.close()

    @asyncio.coroutine
    def on_any_event(self, event):
        pass

    @asyncio.coroutine
    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        # logging.info("Moved %s: from %s to %s", what, event.src_path,
        #              event.dest_path)

        # todo: handle MOVED!!!!!!!!!!!!!!
        try:

            src_path = ProperPath(event.src_path, event.is_directory)
            dest_path = ProperPath(event.dest_path, event.is_directory)
            # determine and get what moved
            item = self.get_item_by_path(src_path)

            # rename
            if isinstance(item, Node) and item.title != dest_path.name:
                if self.already_exists(dest_path):
                    self.session.delete(item)
                    save(self.session)
                else:
                    item.title = dest_path.name
                    save(self.session, item)
            elif isinstance(item, File) and item.name != dest_path.name:
                if self.already_exists(dest_path):
                    self.session.delete(item)
                    save(self.session)
                else:
                    item.name = dest_path.name
                    save(self.session, item)
            # move
            elif src_path != dest_path:
                try:


                    #create a dummy item in old place with .locally deleted so polling does not create new item
                    if isinstance(item, Node):
                        dummy = Node(title=item.title, parent=item.parent, user=item.user, category=item.category, osf_id=item.osf_id)
                    elif isinstance(item, File):
                        dummy = File(name=item.name, parent=item.parent, user=item.user, type=item.type, osf_id=item.osf_id, node=item.node)
                    dummy.locally_deleted = True

                    # move item
                    # fixme: move get_parent_item to above all this because in the time in between dummy is created and item is moved, you have duplicate in db.
                    # fixme: duplicate created because get_parent_item_from_path queries thus flushes to db.
                    new_parent = self._get_parent_item_from_path(dest_path)
                    if isinstance(item, Node):
                        if isinstance(new_parent, Node):
                            item.parent = new_parent
                        elif isinstance(new_parent, File):
                            raise MovedNodeUnderFile
                    elif isinstance(item, File):
                        if isinstance(new_parent, Node):
                            item.parent = None
                            item.node = new_parent.node
                        elif isinstance(new_parent, File):
                            item.parent = new_parent
                            item.node = new_parent.node

                    item.locally_created = True

                    save(self.session, dummy)
                    save(self.session, item)
                except FileNotFoundError:
                    # todo:
                    console_log('tried to move to OSF folder. cant do this.')
                    # item.parent = None




            # todo: log
            # logging.info(item.)



        except FileNotFoundError:
            print('tried to move {} but it doesnt exist in db'.format(event.src_path))

    @asyncio.coroutine
    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
        try:
            # logging.info("Created %s: %s", what, event.src_path)

            src_path = ProperPath(event.src_path, event.is_directory)
            name = src_path.name
            # console_log('create a new thing. it is called',name)
            # create new model
            if not self.already_exists(src_path):
                # console_log('new thing being created does not already exist in db',name)
                # if folder and in top level OSF FOlder, then top_level_node
                if src_path.parent == ProperPath(self.osf_folder, True):
                    if event.is_directory:
                        top_level_node = Node(title=name, user=self.user, locally_created=True)
                        # save
                        save(self.session, top_level_node)
                    else:
                        print("CREATED FILE IN PROJECT AREA.")
                        raise NotADirectoryError

                elif event.is_directory:

                    if File.DEFAULT_PROVIDER in src_path.full_path:  # folder

                        containing_item = self._get_parent_item_from_path(src_path)
                        if isinstance(containing_item, Node):
                            node = containing_item
                        elif isinstance(containing_item, File):
                            node = containing_item.node
                        folder = File(name=name, type=File.FOLDER, user=self.user, locally_created=True,
                                      provider=File.DEFAULT_PROVIDER, node=node)
                        containing_item.files.append(folder)
                        save(self.session, folder)
                    else:  # component

                        new_component = Node(
                            title=name,
                            category=Node.COMPONENT,
                            locally_created=True,
                            user=self.user
                        )

                        parent_component = self._get_parent_item_from_path(src_path)

                        parent_component.components.append(new_component)
                        save(self.session, new_component)

                else:  # if file, then file.

                    containing_item = self._get_parent_item_from_path(src_path)
                    if isinstance(containing_item, Node):
                        node = containing_item
                    elif isinstance(containing_item, File):
                        node = containing_item.node
                    file = File(name=name, type=File.FILE, user=self.user, locally_created=True,
                                provider=File.DEFAULT_PROVIDER, node=node)
                    # console_log('new thing as file object',file)
                    containing_item.files.append(file)
                    save(self.session, file)

                    # console_log('new thing as file object AGAIN in order to check name',file)
                    # log
                    # todo: log

                    # allow for this method to be a coroutine
                    # print('DONE with on created')
                    # yield from asyncio.sleep(1)
        except:
            raise Exception('something wrong in oncreate')

    def already_exists(self, path):
        try:
            self.get_item_by_path(path)
            return True
        except FileNotFoundError:
            return False

    # todo: Evaluate whether I can just ignore DirModifiedEvent's
    @asyncio.coroutine
    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

        # logging.info("Modified %s: %s", what, event.src_path)
        console_log('modifying file. hopefully this is the temp file. event.src_path', event.src_path)

        src_path = ProperPath(event.src_path, event.is_directory)
        # whenever anything gets modified, watchdog crawls up the folder tree all the way up to the osf folder
        # handle osf folder changing or not changing
        if src_path == ProperPath(self.osf_folder, True):
            return  # ignore
            # note: if the OSF folder name is changed, that is NOT modified, but rather move.
            # note: when folder recursively delete, the top folder is modified then removed.
            #       os.path.samefile() tries to open the deleted file and fails. fix is to not open file.

        try:
            # update model

            # get item
            item = self.get_item_by_path(src_path)

            # update hash
            if isinstance(item, File) and item.type == File.FILE:
                item.update_hash()

            # log
            # todo: log

            # save
            save(self.session, item)
            console_log('modifying file. check how temp file is saved back in as', item)
        except FileNotFoundError:
            print('tried to modify {} but it doesnt exist in db'.format(event.src_path))

    @asyncio.coroutine
    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """

        src_path = ProperPath(event.src_path, event.is_directory)
        if 'stream' in src_path.name:
            console_log('deleting file. check if temp file is deleted', src_path.name)
        try:
            # get item
            item = self.get_item_by_path(src_path)

            # put item in delete state
            item.locally_deleted = True

            # log
            # todo: log

            # save
            save(self.session, item)
        except FileNotFoundError:
            # if file does not exist in db, then do nothing.
            print('tried to delete file {} but was not in db'.format(event.src_path))

    # todo: simplify this. perhaps can use rstrip(os.seperator) but unclear if this leads to issues???
    def _get_parent_item_from_path(self, path):
        assert isinstance(path, ProperPath)
        containing_folder_path = path.parent

        if containing_folder_path == ProperPath(self.osf_folder, True):
            raise FileNotFoundError

        return self.get_item_by_path(containing_folder_path)

    # todo: figure out how you can improve this
    def get_item_by_path(self, path):
        assert isinstance(path, ProperPath)
        for node in self.session.query(Node):
            if ProperPath(node.path, True) == path:
                return node
        for file_folder in self.session.query(File):
            file_path = ProperPath(file_folder.path, file_folder.type == File.FOLDER)
            if file_path == path:
                return file_folder
        raise FileNotFoundError

    def dispatch(self, event):
        _method_map = {
            EVENT_TYPE_MODIFIED: self.on_modified,
            EVENT_TYPE_MOVED: self.on_moved,
            EVENT_TYPE_CREATED: self.on_created,
            EVENT_TYPE_DELETED: self.on_deleted,
        }

        handlers = [self.on_any_event, _method_map[event.event_type]]
        for handler in handlers:
            self._loop.call_soon_threadsafe(
                asyncio.async,
                handler(event)
            )

