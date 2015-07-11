__author__ = 'himanshu'
import hashlib
from sqlalchemy import create_engine, Table, ForeignKey, Enum
import datetime
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import SingletonThreadPool
from sqlalchemy.ext.hybrid import hybrid_property
import pytz
import os
Base = declarative_base()
# from sqlalchemy_mptt.mixins import BaseNestedSets





import os


Base = declarative_base()

class User(Base):
     __tablename__ = 'user'

     id = Column(Integer, primary_key=True)
     full_name = Column(String)
     osf_login = Column(String, unique=True)
     osf_password = Column(String)
     osf_path = Column(String)
     oauth_token = Column(String)
     osf_id = Column(String)

     logged_in = Column(Boolean, default=False)


     nodes = relationship(
         "Node",
         backref =backref('user'),
         cascade="all, delete-orphan"
     )

     files = relationship(
         "File",
         backref=backref('user'),
         cascade="all, delete-orphan"
     )

     @hybrid_property
     def projects(self):
         projects =[]
         for node in self.nodes:
             if node.category == Node.PROJECT:
                 projects.append(node)
         return projects

     def __repr__(self):
       return "<User(fullname={}, osf_password={}, osf_path={})>".format(
                             self.full_name, self.osf_password, self.osf_path)

#todo: can have it so that all nodes and subnodes know that they are part of the same user.
class Node(Base):
    __tablename__ = "node"

    PROJECT='project'
    COMPONENT='component'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    # path = Column(String)
    hash = Column(String)
    category = Column(Enum(PROJECT, COMPONENT))
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    osf_id = Column(String)

    locally_created = Column(Boolean, default= False)
    locally_deleted = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey('user.id'))
    parent_id = Column(Integer, ForeignKey('node.id'))
    components = relationship(
        "Node",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan" #todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )
    files = relationship(
        "File",
        backref=backref('node'),
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def path(self):
        """Recursively walk up the path of the node. Top level node joins with the osf folder path of the user
        """
        # +os.path.sep+ instead of os.path.join: http://stackoverflow.com/a/14504695
        if self.parent:
            return os.path.join(self.parent.path, self.title)
        else:
            return os.path.join(self.user.osf_path , self.title)

    @hybrid_property
    def top_level_file_folders(self):
        file_folders =[]
        for file_folder in self.files:
            if file_folder.parent is None:
                file_folders.append(file_folder)
        return file_folders


    def update_hash(self, block_size=2**20):
        pass
        #todo: what to do in this case?

    def __repr__(self):
        return "<Node ({}), category={}, title={}, path={}, parent_id={}>".format(
            self.id, self.category, self.title, self.path, self.parent_id
        )

#todo: can have it so that all files and folders know that they are part of the same component.
class File(Base):
    __tablename__ = "file"

    FOLDER ='folder'
    FILE='file'

    DEFAULT_PROVIDER = 'osfstorage'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # path = Column(String)
    # guid = Column(String)
    hash = Column(String)
    type = Column(Enum(FOLDER,FILE))
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    osf_id = Column(String)
    provider = Column(String, default=DEFAULT_PROVIDER)
    #NOTE: this is called path. It is not any type of file/folder path. Think of it just as an id.
    osf_path = Column(String)


    locally_created = Column(Boolean, default= False)
    locally_deleted = Column(Boolean, default= False)

    user_id = Column(Integer, ForeignKey('user.id'))
    node_id = Column(Integer, ForeignKey('node.id'))
    parent_id = Column(Integer, ForeignKey('file.id'))
    files = relationship(
        "File",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan",  #todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )

    @hybrid_property
    def path(self):
        """Recursively walk up the path of the file/folder. Top level file/folder joins with the path of the containing node.
        """
        # +os.path.sep+ instead of os.path.join: http://stackoverflow.com/a/14504695
        if self.parent:
            return os.path.join(self.parent.path, self.name)
        else:
            return os.path.join(self.node.path ,self.name)

    def update_hash(self, block_size=2**20):
        m = hashlib.md5()
        if self.type == File.FILE:
            with open(self.path,"rb") as f:
                while True:
                    buf = f.read(block_size)
                    if not buf:
                        break
                    m.update(buf)
        else:
            pass
            #todo: what to do in this case?
            # m.update()
        self.hash = m.hexdigest()

    @hybrid_property
    def size(self):
        try:
            return os.stat(self.path).st_size
        except FileNotFoundError: # file was deleted locally
            return 0
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
    #This shows how this should be for various file systems. The current way should handle all of them.
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

def create_session():
    db_file_path = os.path.join(db_dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)
    #todo: figure out if this is safe or not. If not, how to make it safe?????
    # engine = create_engine(url, echo=False, connect_args={'check_same_thread':False})
    engine = create_engine(url, echo=False, connect_args={'check_same_thread':False}, poolclass=SingletonThreadPool)
    session_factory = sessionmaker(bind=engine)
    global Session
    Session = scoped_session(session_factory)
    #todo: figure out a safer way to do this
    # global session

# evaluatation of autocommit/autoflush for models was decidedly not a good idea.
# todo: I think evaluation was WRONG. if does not commit until added to session, then autocommit is GOOD.
#todo: if you do use save method, then you need to standardize rest of code to use this method
def save(session, item=None):
    if item:
        session.add(item)
    try:
        session.commit()
    except:
        session.rollback()
        raise

#todo: probably okay to have a method that finds a component by guid.


