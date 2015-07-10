"""
This is the most important file in the system. OSFEventHandler is responsible for updating the models,
storing the data into the db, and then sending a request to the remote server.
"""

import os
import logging

from watchdog.events import FileSystemEventHandler

from osfoffline.models import User,Node,File, get_session


EVENT_TYPE_MOVED = 'moved'
EVENT_TYPE_DELETED = 'deleted'
EVENT_TYPE_CREATED = 'created'
EVENT_TYPE_MODIFIED = 'modified'
import asyncio


def console_log(variable_name, variable_value):
    print("DEBUG: {}: {}".format(variable_name, variable_value))




class OSFEventHandler(FileSystemEventHandler):
    """
    Base file system event handler that you can override methods from.
    """
    def __init__(self, OSFFolder, db_url, user, loop):
        super().__init__()
        self._loop = loop or asyncio.get_event_loop()
        self.OSFFolder = OSFFolder

        self.session = get_session()
        self.user = self.session.query(User).first() #assume only one user for now!!!!!

        # self.queue = queue()
        # self._running = True


    # def pause(self):
    #     self._running = False
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
    def on_any_event(self, event):pass

    @asyncio.coroutine
    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        # logging.info("Moved %s: from %s to %s", what, event.src_path,
        #              event.dest_path)


        #todo: handle renamed!!!!!!!!!
        try:
            # determine and get what moved
            item = self.get_item_by_path(event.src_path)

            # update item's position
            try:
                item.parent = self._get_parent_item_from_path(event.dest_path)
            except FileNotFoundError:
                item.parent = None

            # rename folder
            if isinstance(item, Node) and item.title != os.path.basename(event.dest_path):
                item.title = os.path.basename(event.dest_path)
            elif isinstance(item, File) and item.name != os.path.basename(event.dest_path):
                item.name = os.path.basename(event.dest_path)
            else:
                raise ValueError('some messed up thing was moved')

            #todo: log
            # logging.info(item.)

            #save
            self.save(item)
        except FileNotFoundError:
            print('tried to move {} but it doesnt exist in db'.format(event.src_path))
            pass

        #allow for this method to be a coroutine
        # print('DONE with on moved')
        # yield '1'


    @asyncio.coroutine
    def on_created(self,event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
        try:
            what = 'directory' if event.is_directory else 'file'
            # logging.info("Created %s: %s", what, event.src_path)

            name= os.path.basename(event.src_path)

            # create new model
            if not self.already_exists(event.src_path):
                #if folder and in top level OSF FOlder, then project
                if os.path.dirname(event.src_path)==self.OSFFolder:
                    if event.is_directory:
                        project = Node( title=name, category=Node.PROJECT, user=self.user, locally_created=True )
                        #save
                        self.save(project)
                    else:
                        print("CREATED FILE IN PROJECT AREA. ")
                        raise NotADirectoryError

                elif event.is_directory:

                    if File.DEFAULT_PROVIDER in event.src_path: #folder
                        folder = File(name=name, type=File.FOLDER, user=self.user, locally_created=True, provider=File.DEFAULT_PROVIDER)
                        containing_item = self._get_parent_item_from_path(event.src_path)
                        containing_item.files.append(folder)
                        self.save(folder)
                    else: # component
                        console_log('start','debugging')
                        new_component = Node(
                            title=name,
                            category=Node.COMPONENT,
                            locally_created=True,
                            user=self.user
                            )
                        console_log('new_component.title',new_component.title)
                        parent_component = self._get_parent_item_from_path(event.src_path)

                        parent_component.components.append(new_component)
                        self.save(new_component)
                        console_log('parent_component.title',parent_component.title)
                        console_log('parent_component.components',parent_component.components)
                        console_log('parent_component.files',parent_component.files)
                else: # if file, then file.
                    file = File(name=name,type=File.FILE, user=self.user, locally_created=True, provider=File.DEFAULT_PROVIDER)
                    containing_item = self._get_parent_item_from_path(event.src_path)
                    containing_item.files.append(file)
                    self.save(file)


                #log
                #todo: log


            #allow for this method to be a coroutine
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

    #todo: Evaluate whether I can just ignore DirModifiedEvent's
    @asyncio.coroutine
    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        # logging.info("Modified %s: %s", what, event.src_path)

        #todo: change all path comparisons to os.path.samefile
        # whenever anything gets modified, watchdog crawls up the folder tree all the way up to the osf folder
        # handle osf folder changing or not changing
        if os.path.exists(event.src_path) and os.path.exists(self.OSFFolder) and os.path.samefile(event.src_path, self.OSFFolder):
            return # ignore
            # note: if the OSF folder name is changed, that is NOT modified, but rather move.
            # note: when folder recursively delete, the top folder is modified then removed.
            #       os.path.samefile() tries to open the deleted file and fails. fix is to not open file.

        try:
            # update model

            # get item
            item = self.get_item_by_path(event.src_path)

            # update hash
            item.update_hash()


            #send to server
            #todo: send to server

            #log
            #todo: log

            #save
            self.save(item)
        except FileNotFoundError:
            print('tried to modify {} but it doesnt exist in db'.format(event.src_path))
            pass
        #allow for this method to be a coroutine
        # yield from asyncio.sleep(1)
        # print('DONE with on modified')
        # yield '1'


    @asyncio.coroutine
    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        logging.info("Deleted %s: %s", what, event.src_path)


        try:

            # get item
            item = self.get_item_by_path(event.src_path)

            # put item in delete state
            item.locally_deleted = True

            #log
            #todo: log


            #save
            self.save(item)
        except FileNotFoundError:
            # if file does not exist in db, then do nothing.
            print('tried to delete file {} but was not in db'.format(event.src_path))
            pass
        #allow for this method to be a coroutine
        print('DONE with on delete')
        # yield '1'


    #todo: simplify this. perhaps can use rstrip(seperator) but unclear if this leads to issues???
    def _get_parent_item_from_path(self, path):
        containing_folder_path = os.path.dirname(path)

        if containing_folder_path == self.OSFFolder:
            raise FileNotFoundError
        # what can happen is that the rightmost
        try:
            return self.get_item_by_path(containing_folder_path)
        except FileNotFoundError:
            containing_folder_path = os.path.dirname(containing_folder_path)
            return self.get_item_by_path(containing_folder_path)


    #todo: figure out how you can improve this
    def get_item_by_path(self,path):
        for node in self.session.query(Node):
            if node.path == path:
                return node
        for file_folder in self.session.query(File):
            if file_folder.path == path:
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


