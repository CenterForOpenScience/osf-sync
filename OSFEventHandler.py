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
        self.user = user



    def save(self):
        try:
            self.session.commit()
        except:
            self.session.rollback()
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
        item = self.session.query(Node).filter(Node.path == event.src_path).first()
        if not item:
            item = self.session.query(File).filter(File.path == event.src_path).first()
            if not item:
                raise FileNotFoundError
        #update path
        item.path = event.dest_path
        #todo: log
        # logging.info(item.)

        #save
        self.save()

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
                    project = Node(path=event.src_path, title=name, category=Node.PROJECT)
                    self.session.add(project)
                else:
                    print("CREATED FILE IN PROJECT AREA. ")
                    raise NotADirectoryError
            #if folder, then assume Folder
            elif event.is_directory:
                folder = File(path=event.src_path, name=name, type=File.FOLDER)
                containing_item = self._get_parent_item_from_path(event.src_path)
                containing_item.files.append(folder)
            else: # if file, then file.
                file = File(path=event.src_path, name=name,type=File.FILE)
                containing_item = self._get_parent_item_from_path(event.src_path)
                containing_item.files.append(file)


            #log
            #todo: log



            #save
            self.save()

    def already_exists(self, path):
        data1 = self.session.query(Node).filter(Node.path==path).first()
        if data1:
            return True
        data2 = self.session.query(File).filter(File.path == path).first()
        if data2:
            return True
        return False

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
        item = self.session.query(Node).filter(Node.path == event.src_path).first()
        if not item:
            item = self.session.query(File).filter(File.path == event.src_path).first()
            if not item:
                raise FileNotFoundError

        # update hash, date_modified
        item.update_hash()
        item.update_time()

        #send to server
        #todo: send to server

        #log
        #todo: log

        #save
        self.save()



    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """

        what = 'directory' if event.is_directory else 'file'
        logging.info("Deleted %s: %s", what, event.src_path)

        # import pdb;pdb.set_trace()


        # get item
        item = self.session.query(Node).filter(Node.path == event.src_path).first()
        if not item:
            item = self.session.query(File).filter(File.path == event.src_path).first()
            if not item:
                raise FileNotFoundError

        #send to server
        #todo: send to server

        #log
        #todo: log

        # remove model
        self.session.delete(item)


        #save
        self.save()


    def _get_parent_item_from_path(self, path):
        containing_folder = os.path.dirname(path)

        while True:
            if containing_folder == self.OSFFolder:
                raise FileNotFoundError
            folder = self.session.query(File).filter(File.path == containing_folder).first()
            if folder:
                return folder
            else:
                component = self.session.query(Node).filter(Node.path == containing_folder).first()
                if component:
                    return component
                else:
                    containing_folder = os.path.dirname(containing_folder)



