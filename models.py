__author__ = 'himanshu'

import sqlite3
import sqlalchemy
import hashlib
from sqlalchemy import create_engine, Table, ForeignKey, Enum
from datetime import date, datetime
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
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
     projects = relationship(
         "Node",
         cascade="all, delete-orphan"
     )

     def __repr__(self):
       return "<User(fullname={}, osf_password={}, osf_path={})>".format(
                             self.fullname, self.osf_password, self.osf_path)

#todo: can have it so that all nodes and subnodes know that they are part of the same user.
#todo: http://docs.sqlalchemy.org/en/rel_1_0/orm/self_referential.html#composite-adjacency-lists
class Node(Base):
    __tablename__ = "node"

    PROJECT='project'
    COMPONENT='component'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    guid = Column(String)
    hash = Column(String)
    category = Column(Enum(PROJECT, COMPONENT))
    nid = Column(String) # todo: GUID versus NID
    date_modified = Column(DateTime)

    user_id = Column(Integer, ForeignKey('user.id'))
    parent_id = Column(Integer, ForeignKey('node.id'))
    components = relationship(
        "Node",
        backref=backref('parent', remote_side=[id]),
        # cascade="all, delete-orphan" #todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )
    files = relationship("File")



    def update_hash(self, blocksize=2**20):
        pass
        #todo: what to do in this case?

    def update_time(self, dt=None):
        if dt:
            self.date_modified = dt
        else:
            self.date_modified = datetime.now()

    def __repr__(self):
        return "<Node ({}), category={}, name={}, path={}, parent_id={}>".format(
            self.id, self.category, self.name, self.path, self.parent_id
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
    guid = Column(String)
    hash = Column(String)
    type = Column(Enum(FOLDER,FILE))
    date_modified = Column(DateTime)

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
            self.id, self.type, self.name, self.path, self.parent_id
        )

def create_models(dir):
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
    db_file_path = os.path.join(dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)

    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)



#todo: why pass in dir? models should be able to handle knowing where the db is.
def create_session(dir):
    db_file_path = os.path.join(dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)
    engine = create_engine(url, echo=False)
    Session = sessionmaker()
    Session.configure(bind=engine)
    return Session()

#todo: probably okay to have a method that finds a component by guid.

