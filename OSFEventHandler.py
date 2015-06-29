"""
This is the most important file in the system. OSFEventHandler is responsible for updating the models,
storing the data into the db, and then sending a request to the remote server.
"""

import os
import json
import logging
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool
from watchdog.events import FileSystemEventHandler
from sqlalchemy import create_engine
from models import User,Node,File, get_session
import requests
import queue

class OSFEventHandler(FileSystemEventHandler):
    """
    Base file system event handler that you can override methods from.
    """
    def __init__(self, OSFFolder, db_url, user):
        super(OSFEventHandler, self).__init__()
        self.OSFFolder = OSFFolder

        db_file_path = os.path.join(db_url, 'osf.db')
        url = 'sqlite:///{}'.format(db_file_path)
        #todo: figure out if this is safe or not. If not, how to make it safe?????
        # engine = create_engine(url, echo=False, connect_args={'check_same_thread':False})
        engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
        session_factory = sessionmaker(bind=engine)
        global Session
        Session = scoped_session(session_factory)
        self.session = Session()
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


        #todo: handle renamed!!!!!!!!!

        # determine and get what moved
        item = self.get_item_by_path(event.src_path)

        # update item's position
        try:
            item.parent = self._get_parent_item_from_path(event.dest_path)
        except FileNotFoundError:
            item.parent = None

        #todo: log
        # logging.info(item.)

        #save
        self.save(item)

        #todo: send data to server



    def on_created(self,event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
        what = 'directory' if event.is_directory else 'file'
        logging.info("Created %s: %s", what, event.src_path)

        name= os.path.basename(event.src_path)

        # create new model

        if not self.already_exists(event.src_path):
            #if folder and in top level OSF FOlder, then project
            if os.path.dirname(event.src_path)==self.OSFFolder:
                if event.is_directory:
                    project = Node( title=name, category=Node.PROJECT, user=self.user, created=True)
                    #save
                    self.save(project)
                else:
                    print("CREATED FILE IN PROJECT AREA. ")
                    raise NotADirectoryError
            #if folder, then assume Folder
            elif event.is_directory:
                folder = File(name=name, type=File.FOLDER, user=self.user, created=True)
                containing_item = self._get_parent_item_from_path(event.src_path)
                containing_item.files.append(folder)
                self.save(folder)
            else: # if file, then file.
                file = File(name=name,type=File.FILE, user=self.user, created=True)
                containing_item = self._get_parent_item_from_path(event.src_path)
                containing_item.files.append(file)
                self.save(file)


            #log
            #todo: log





    def already_exists(self, path):
        try:
            self.get_item_by_path(path)
            return False
        except FileNotFoundError:
            return True

    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        logging.info("Modified %s: %s", what, event.src_path)

        #todo: change all path comparisons to os.path.samefile
        # whenever anything gets modified, watchdog crawls up the folder tree all the way up to the osf folder
        # handle osf folder changing or not changing
        if os.path.exists(event.src_path) and os.path.exists(self.OSFFolder) and os.path.samefile(event.src_path, self.OSFFolder):
            return # ignore
            # note: if the OSF folder name is changed, that is NOT modified, but rather move.
            # note: when folder recursively delete, the top folder is modified then removed.
            #       os.path.samefile() tries to open the deleted file and fails. fix is to not open file.


        # update model

        # get item
        item = self.get_item_by_path(event.src_path)

        # update hash, date_modified
        item.update_hash()
        item.update_time()

        #send to server
        #todo: send to server

        #log
        #todo: log

        #save
        self.save(item)



    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        logging.info("Deleted %s: %s", what, event.src_path)



        # get item
        item = self.get_item_by_path(event.src_path)

        # put item in delete state
        item.deleted = True

        #log
        #todo: log


        #save
        self.save(item)


    #todo: simplify this. perhaps can use rstrip(seperator) but unclear if this leads to issues???
    def _get_parent_item_from_path(self, path):
        containing_folder_path = os.path.dirname(path)

        if containing_folder_path == self.OSFFolder:
            raise FileNotFoundError

        #what can happen is that the rightmost
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
