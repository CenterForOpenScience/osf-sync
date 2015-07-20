__author__ = 'himanshu'
import hashlib
import datetime
import os
from appdirs import user_data_dir
# from settings import PROJECT_NAME, PROJECT_AUTHOR
from sqlalchemy import create_engine, ForeignKey, Enum
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.hybrid import hybrid_property
Base = declarative_base()
import shutil

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    osf_login = Column(String, unique=True)
    osf_password = Column(String)
    osf_local_folder_path = Column(String)
    oauth_token = Column(String)
    osf_id = Column(String)

    logged_in = Column(Boolean, default=False)

    nodes = relationship(
        "Node",
        backref=backref('user'),
        cascade="all, delete-orphan"
    )

    files = relationship(
        "File",
        backref=backref('user'),
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def top_level_nodes(self):
        top_nodes = []
        for node in self.nodes:
            if node.category == Node.PROJECT:
                top_nodes.append(node)
        return top_nodes

    def __repr__(self):
        return "<User(fullname={}, osf_password={}, osf_local_folder_path={})>".format(
            self.full_name, self.osf_password, self.osf_local_folder_path)




# todo: can have it so that all nodes and subnodes know that they are part of the same user.
class Node(Base):
    __tablename__ = "node"

    PROJECT = 'project'
    COMPONENT = 'component'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    # path = Column(String)
    hash = Column(String)
    category = Column(Enum(PROJECT, COMPONENT))
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    osf_id = Column(String)

    locally_created = Column(Boolean, default=False)
    locally_deleted = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('node.id'))
    components = relationship(
        "Node",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
        # todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )
    files = relationship(
        "File",
        backref=backref('node'),
        cascade="all, delete-orphan"
    )


    @hybrid_property
    def path(self):
        """Recursively walk up the path of the node. Top level node joins with the osf folder path of the user
        """
        # +os.path.sep+ instead of os.path.join: http://stackoverflow.com/a/14504695
        if self.parent:
            return os.path.join(self.parent.path, self.title)
        else:
            return os.path.join(self.user.osf_local_folder_path, self.title)

    @hybrid_property
    def top_level_file_folders(self):
        file_folders = []
        for file_folder in self.files:
            if file_folder.parent is None:
                file_folders.append(file_folder)
        return file_folders

    def update_hash(self, block_size=2 ** 20):
        pass
        # todo: what to do in this case?

    def __repr__(self):
        return "<Node ({}), category={}, title={}, path={}, parent_id={}>".format(
            self.id, self.category, self.title, self.path, self.parent_id
        )


# todo: can have it so that all files and folders know that they are part of the same component.
class File(Base):
    __tablename__ = "file"

    FOLDER = 'folder'
    FILE = 'file'

    DEFAULT_PROVIDER = 'osfstorage'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    # path = Column(String)
    # guid = Column(String)
    hash = Column(String)
    type = Column(Enum(FOLDER, FILE))
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    osf_id = Column(String)
    provider = Column(String, default=DEFAULT_PROVIDER)
    # NOTE: this is called path. It is not any type of file/folder path. Think of it just as an id.
    osf_path = Column(String)

    locally_created = Column(Boolean, default=False)
    locally_deleted = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey('user.id'))
    node_id = Column(Integer, ForeignKey('node.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('file.id'))
    files = relationship(
        "File",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan",
        # todo: watchdog crawls up so cascade makes things fail on recursive delete. may want to have delete just ignore fails.
    )

    @hybrid_property
    def has_parent(self):
        return self.parent is not None

    @hybrid_property
    def path(self):
        """Recursively walk up the path of the file/folder. Top level file/folder joins with the path of the containing node.
        """
        # +os.path.sep+ instead of os.path.join: http://stackoverflow.com/a/14504695
        if self.parent:
            return os.path.join(self.parent.path, self.name)
        else:
            return os.path.join(self.node.path, self.name)

    def update_hash(self, block_size=2 ** 20):
        m = hashlib.md5()
        if self.type == File.FILE:
            with open(self.path, "rb") as f:
                while True:
                    buf = f.read(block_size)
                    if not buf:
                        break
                    m.update(buf)
        else:
            pass
            # todo: what to do in this case?
            # m.update()
        self.hash = m.hexdigest()

    @hybrid_property
    def size(self):
        try:
            return os.stat(self.path).st_size
        except FileNotFoundError:  # file was deleted locally
            return 0

    def __repr__(self):
        return "<File ({}), type={}, name={}, path={}, parent_id={}>".format(
            self.id, self.type, self.name, self.path, self.parent
        )

db_dir = ''
Session = None


def setup_db(dir=None):
    global db_dir
    if dir:
        db_dir=dir
    # else:
    #     db_dir = user_data_dir(PROJECT_NAME, PROJECT_AUTHOR)
    create_models()
    create_session()

def teardown_db(dir):
    global db_dir
    shutil.rmtree(db_dir)

def get_session():
    return Session()


def create_models():
    """ Create sql alchemy engine and models for all file systems.
    """
    if not os.path.isdir(db_dir):
        os.makedirs(db_dir)
    db_file_path = os.path.join(db_dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)


def create_session():
    """
    this function sets up the Session global variable using the previously setup db.
    The Session object in this case uses the identity map pattern.
    There is a single Session map. Whenever we create a new session via get_session(),
    we are really just getting the currently stored session in that thread.
    Session object here refers to getting a db session from a map from identity map pattern ma
    :return:
    """
    db_file_path = os.path.join(db_dir, 'osf.db')
    url = 'sqlite:///{}'.format(db_file_path)


    # for this application, that should only lead to 2 connections in total
    # todo: figure out if this is safe or not. If not, how to make it safe?????
    # engine = create_engine(url, echo=False, connect_args={'check_same_thread':False})
    engine = create_engine(url, echo=False)
    session_factory = sessionmaker(bind=engine)
    # figure out safer way to do this
    global Session
    Session = scoped_session(session_factory)



# todo: probably okay to have a method that finds a component by guid.

# evaluatation of autocommit/autoflush for models was decidedly not a good idea.
# I think evaluation was WRONG. if does not commit until added to session, then autocommit is GOOD.
# if you do use save method, then you need to standardize rest of code to use this method
# autocommit suggested to be BAD idea by their website. So don't do  it.
def save(session, item=None):
    if item:
        session.add(item)
    try:
        session.commit()
    except:
        session.rollback()
        raise
