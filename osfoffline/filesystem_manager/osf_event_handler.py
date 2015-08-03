"""
This is the most important file in the system. OSFEventHandler is responsible for updating the models,
storing the data into the db, and then sending a request to the remote server.
"""
import asyncio

from watchdog.events import FileSystemEventHandler, DirModifiedEvent
import logging
from osfoffline.database_manager.models import Node, File,User
from osfoffline.database_manager.db import session
from osfoffline.database_manager.utils import save, session_scope
from osfoffline.utils.path import ProperPath
from osfoffline.exceptions.event_handler_exceptions import MovedNodeUnderFile

EVENT_TYPE_MOVED = 'moved'
EVENT_TYPE_DELETED = 'deleted'
EVENT_TYPE_CREATED = 'created'
EVENT_TYPE_MODIFIED = 'modified'


class OSFEventHandler(FileSystemEventHandler):
    """
    Base file system event handler that you can override methods from.
    """
    def __init__(self, osf_folder, db_url, user, loop):
        super().__init__()
        self._loop = loop or asyncio.get_event_loop()
        self.osf_folder = osf_folder


        self.user = session.query(User).filter(User.logged_in).one()



    def close(self):
        pass

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

        try:

            src_path = ProperPath(event.src_path, event.is_directory)
            dest_path = ProperPath(event.dest_path, event.is_directory)
            # determine and get what moved
            item = self.get_item_by_path(src_path)

            # rename
            if isinstance(item, Node) and item.title != dest_path.name:
                if self.already_exists(dest_path):
                    session.delete(item)
                    save(session)
                else:
                    item.title = dest_path.name
                    save(session, item)
            elif isinstance(item, File) and item.name != dest_path.name:
                if self.already_exists(dest_path):
                    session.delete(item)
                    save(session)
                else:
                    item.name = dest_path.name
                    item.locally_renamed = True
                    save(session, item)
            # move
            elif src_path != dest_path:
                try:

                    # check if file already exists in this moved location. If so, delete it.
                    try:
                        item_to_replace = self.get_item_by_path(dest_path)
                        session.delete(item_to_replace)
                        save(session)
                    except FileNotFoundError:
                        pass

                    new_parent = self._get_parent_item_from_path(dest_path)

                    # create a dummy item in old place with .locally deleted so polling does not create new item
                    if isinstance(item, Node):
                        dummy = Node(title=item.title, parent=item.parent, user=item.user, category=item.category, osf_id="DELETE{}DUMMY".format(item.osf_id))
                    elif isinstance(item, File):
                        dummy = File(name=item.name, parent=item.parent, user=item.user, type=item.type, osf_id="DELETE{}DUMMY".format(item.osf_id), node=item.node)
                    dummy.locally_deleted = True

                    # move item
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

                    item.locally_create_children()

                    save(session, dummy)
                    save(session, item)
                except FileNotFoundError:
                    logging.warning('tried to move to OSF folder. cant do this.')
                    # item.parent = None







        except FileNotFoundError:
            logging.warning('tried to move {} but it doesnt exist in db'.format(event.src_path))

    @asyncio.coroutine
    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """

        try:

            src_path = ProperPath(event.src_path, event.is_directory)
            name = src_path.name

            # create new model
            if not self.already_exists(src_path):

                # if folder and in top level OSF FOlder, then top_level_node
                if src_path.parent == ProperPath(self.osf_folder, True):
                    if event.is_directory:
                        top_level_node = Node(title=name, user=self.user, locally_created=True)
                        # save
                        save(session, top_level_node)
                    else:
                        #todo: can just delete the file right here and give an alert.
                        logging.warning("CREATED FILE IN PROJECT AREA.")
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
                        save(session, folder)
                    else:  # child node

                        new_child_node = Node(
                            title=name,
                            category=Node.COMPONENT,
                            locally_created=True,
                            user=self.user
                        )

                        parent_component = self._get_parent_item_from_path(src_path)

                        parent_component.child_nodes.append(new_child_node)
                        save(session, new_child_node)

                else:  # if file, then file.

                    containing_item = self._get_parent_item_from_path(src_path)
                    if isinstance(containing_item, Node):
                        node = containing_item
                    elif isinstance(containing_item, File):
                        node = containing_item.node
                    file = File(name=name, type=File.FILE, user=self.user, locally_created=True,
                                provider=File.DEFAULT_PROVIDER, node=node)

                    containing_item.files.append(file)
                    try:
                        # if we can't update the hash immediately after creating, then it is likely a
                        # fake file or something of the sort. Thus, we can just ignore this event.
                        file.update_hash()
                    except FileNotFoundError:
                        return
                    save(session, file)



        except:
            raise Exception('something wrong in oncreate')

    def already_exists(self, path):
        try:
            self.get_item_by_path(path)
            return True
        except FileNotFoundError:
            return False

    @asyncio.coroutine
    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

        if isinstance(event, DirModifiedEvent):
            return



        src_path = ProperPath(event.src_path, event.is_directory)
        try:
            # update model

            # get item
            item = self.get_item_by_path(src_path)

            # update hash
            if isinstance(item, File) and item.is_file:
                item.update_hash()



            # save
            save(session, item)

        except FileNotFoundError:
            logging.warning('tried to modify {} but it doesnt exist in db'.format(event.src_path))

    @asyncio.coroutine
    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """

        src_path = ProperPath(event.src_path, event.is_directory)
        try:
            # get item
            item = self.get_item_by_path(src_path)

            # put item in delete state
            item.locally_deleted = True

            # if item cannot/should not be deleted online, then just delete here.. it will be recreated.
            if isinstance(item, Node) or (isinstance(item, File) and item.is_provider):
                session.delete(item)
                save(session)


            # save
            save(session, item)
        except FileNotFoundError:
            # if file does not exist in db, then do nothing.
            logging.warning('tried to delete file {} but was not in db'.format(event.src_path))


    def _get_parent_item_from_path(self, path):
        assert isinstance(path, ProperPath)
        containing_folder_path = path.parent

        if containing_folder_path == ProperPath(self.osf_folder, True):
            raise FileNotFoundError

        return self.get_item_by_path(containing_folder_path)

    # todo: figure out how you can improve this
    def get_item_by_path(self, path):
        assert isinstance(path, ProperPath)
        for node in session.query(Node):
            if ProperPath(node.path, True) == path:
                return node
        for file_folder in session.query(File):
            file_path = ProperPath(file_folder.path, file_folder.is_folder)
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

