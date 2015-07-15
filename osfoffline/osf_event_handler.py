"""
This is the most important file in the system. OSFEventHandler is responsible for updating the models,
storing the data into the db, and then sending a request to the remote server.
"""
from watchdog.events import FileSystemEventHandler
from models import User, Node, File, get_session
import os
import logging
import asyncio
from path import ProperPath
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
        self.user = self.session.query(User).first()  # assume only one user for now!!!!!

        # self.queue = queue()
        # self._running = True
    # def pause(self):
    # self._running = False
    # def unpause(self):
    #     while not self.queue.empty():
    #         event = self.queue.get()
    #         self.dispatch(event)
    #     self._running = True

    # def check_pause(self,func, event):
    #     if self._running:
    #         return func(event)
    #     else:
    #         self.queue.put(event)

    def save(self, item):
        if item:
            self.session.add(item)
        try:
            self.session.commit()
        except:
            raise

    def close(self):
        self.save()
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

        # todo: handle renamed!!!!!!!!!
        try:
            console_log('1','1')
            src_path = ProperPath(event.src_path, event.is_directory)
            console_log('2','2')
            dest_path = ProperPath(event.dest_path, event.is_directory)
            console_log('3','3')
            # determine and get what moved
            item = self.get_item_by_path(src_path)
            console_log('4','4')

            # update item's position
            try:
                item.parent = self._get_parent_item_from_path(dest_path)
            except FileNotFoundError:
                item.parent = None
            console_log('5','5')

            # rename folder
            if isinstance(item, Node) and item.title != dest_path.name:
                item.title = dest_path.name
            elif isinstance(item, File) and item.name != dest_path.name:
                console_log('6','6')
                item.name = dest_path.name
                console_log('item.name',item.name)
            else:
                raise ValueError('some messed up thing was moved')

            # todo: log
            # logging.info(item.)
            console_log('7','7')
            # save
            self.save(item)
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

            # create new model
            if not self.already_exists(src_path):
                # if folder and in top level OSF FOlder, then project
                if src_path.parent == ProperPath(self.osf_folder, True):
                    if event.is_directory:
                        project = Node(title=name, category=Node.PROJECT, user=self.user, locally_created=True)
                        # save
                        self.save(project)
                    else:
                        print("CREATED FILE IN PROJECT AREA. ")
                        raise NotADirectoryError

                elif event.is_directory:

                    if File.DEFAULT_PROVIDER in src_path.full_path:  # folder
                        console_log('src_path',src_path)
                        containing_item = self._get_parent_item_from_path(src_path)
                        if isinstance(containing_item, Node):
                            node = containing_item
                        elif isinstance(containing_item, File):
                            node = containing_item.node
                        folder = File(name=name, type=File.FOLDER, user=self.user, locally_created=True,
                                      provider=File.DEFAULT_PROVIDER, node=node)
                        containing_item.files.append(folder)
                        self.save(folder)
                    else:  # component

                        new_component = Node(
                            title=name,
                            category=Node.COMPONENT,
                            locally_created=True,
                            user=self.user
                        )

                        parent_component = self._get_parent_item_from_path(src_path)

                        parent_component.components.append(new_component)
                        self.save(new_component)

                else:  # if file, then file.
                    containing_item = self._get_parent_item_from_path(src_path)
                    if isinstance(containing_item, Node):
                        node = containing_item
                    elif isinstance(containing_item, File):
                        node = containing_item.node
                    file = File(name=name, type=File.FILE, user=self.user, locally_created=True,
                                provider=File.DEFAULT_PROVIDER, node=node)
                    containing_item.files.append(file)
                    self.save(file)

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
            item.update_hash()

            # send to server
            # todo: send to server

            # log
            # todo: log

            # save
            self.save(item)
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

        try:
            # get item
            item = self.get_item_by_path(src_path)

            # put item in delete state
            item.locally_deleted = True

            # log
            # todo: log

            # save
            self.save(item)
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

    # def normalize_path(self, path, is_dir):
    #     normalized_path = path
    #
    #     if path.endswith(os.sep) and not is_dir:
    #         normalized_path = path[0:-1* len(os.sep)]  # remove seperator
    #     elif not path.endswith(os.sep) and is_dir:
    #         normalized_path = os.path.join(path, '')  # add seperator
    #
    #     return normalized_path

