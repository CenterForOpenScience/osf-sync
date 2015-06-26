__author__ = 'himanshu'


import sqlalchemy
import hashlib
from sqlalchemy import create_engine, Table, ForeignKey, Enum
from datetime import date, datetime
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import SingletonThreadPool
# from sqlalchemy_mptt.mixins import BaseNestedSets

import os


Base = declarative_base()

class User(Base):
     __tablename__ = 'user'

     id = Column(Integer, primary_key=True)
     fullname = Column(String)
     osf_login = Column(String)
     osf_password = Column(String)
     osf_path = Column(String)
     oauth_token = Column(String)
     osf_id = Column(String)

     #todo: enforce category = PROJECT condition for projects
     folders = relationship(
         "Folder",
         backref =backref('user', remote_side=[id]) ,
         cascade="all, delete-orphan"
     )

     files = relationship(
         "File",
         backref=backref('user', remote_side=[id]),
         cascade="all, delete-orphan"
     )

     def __repr__(self):
       return "<User(fullname={}, osf_password={}, osf_path={})>".format(
                             self.fullname, self.osf_password, self.osf_path)

#todo: can have it so that all nodes and subnodes know that they are part of the same user.
#todo: http://docs.sqlalchemy.org/en/rel_1_0/orm/self_referential.html#composite-adjacency-lists
class Folder(Base):
    __tablename__ = "folder"

    PROJECT='project'
    COMPONENT='component'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    path = Column(String)
    hash = Column(String)
    category = Column(Enum(PROJECT, COMPONENT))
    date_modified = Column(DateTime)
    osf_id = Column(String)

    user_id = Column(Integer, ForeignKey('user.id'))
    parent_id = Column(Integer, ForeignKey('node.id'))
    components = relationship(
        "Node",
        backref=backref('parent', remote_side=[id]),
        # cascade="all, delete-orphan" #todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )
    files = relationship(
        "File",
        backref=backref('node', remote_side=[id])
    )



    def update_hash(self, blocksize=2**20):
        pass
        #todo: what to do in this case?

    def update_time(self, dt=None):
        if dt:
            self.date_modified = dt
        else:
            self.date_modified = datetime.now()

    def __repr__(self):
        return "<Node ({}), category={}, title={}, path={}, parent_id={}>".format(
            self.id, self.category, self.title, self.path, self.parent_id
        )


#todo: can have it so that all files and folders know that they are part of the same component.
#todo: http://docs.sqlalchemy.org/en/rel_1_0/orm/self_referential.html#composite-adjacency-lists
class File(Base):
    __tablename__ = "file"

    FOLDER ='folder'
    FILE='file'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    # guid = Column(String)
    hash = Column(String)
    type = Column(Enum(FOLDER,FILE))
    date_modified = Column(DateTime)
    osf_id = Column(String)

    user_id = Column(Integer, ForeignKey('user.id'))
    node_id = Column(Integer, ForeignKey('node.id'))
    parent_id = Column(Integer, ForeignKey('file.id'))
    files = relationship(
        "File",
        backref=backref('parent', remote_side=[id]),
        # cascade="all, delete-orphan",  #todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )

    def update_hash(self, blocksize=2**20):
        m = hashlib.md5()
        if self.type == File.FILE:
            with open(self.path,"rb") as f:
                while True:
                    buf = f.read(blocksize)
                    if not buf:
                        break
                    m.update(buf)
        else:
            pass
            #todo: what to do in this case?
            # m.update()
        self.hash = m.hexdigest()

    def update_time(self, dt=None):
        if dt:
            self.date_modified = dt
        else:
            self.date_modified = datetime.now()

    def __repr__(self):
        return "<File ({}), type={}, name={}, path={}, parent_id={}>".format(
            self.id, self.type, self.name, self.path, self.parent
        )

db_dir = ''
Session = None
def setup_db(dir):
    global db_dir
    db_dir = dir
    create_models()
    create_session()

def get_session():
    return Session()

def create_models():
    """
    #TODO: handle different file systems.
    # sqlite://<nohostname>/<path>
    # where <path> is relative:
    engine = create_engine('sqlite:///foo.db')
    And for an absolute file path, the three slashes are followed by the absolute path:

    #Unix/Mac - 4 initial slashes in total
    engine = create_engine('sqlite:////absolute/path/to/foo.db')
    #Windows
    engine = create_engine('sqlite:///C:\\path\\to\\foo.db')
    #Windows alternative using raw string
    engine = create_engine(r'sqlite:///C:\path\to\foo.db')
    """
    db_file_path = os.path.join(db_dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)

    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)


# session = None

#todo: why pass in dir? models should be able to handle knowing where the db is.
#todo: remove
def create_session():
    db_file_path = os.path.join(db_dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)
    #todo: figure out if this is safe or not. If not, how to make it safe?????
    # engine = create_engine(url, echo=False, connect_args={'check_same_thread':False})
    engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
    session_factory = sessionmaker(bind=engine)
    global Session
    Session = scoped_session(session_factory)
    #todo: figure out a safer way to do this
    # global session


# def create_session(dir):
#
#     if session is None:
#         _create_session(dir)
#     return session


#todo: probably okay to have a method that finds a component by guid.

