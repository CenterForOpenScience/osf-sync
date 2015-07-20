__author__ = 'himanshu'
import hashlib
import datetime
import os

from sqlalchemy import create_engine, ForeignKey, Enum
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session, validates
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.hybrid import hybrid_property
Base = declarative_base()


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
            if node.top_level:
                top_nodes.append(node)
        return top_nodes



    def __repr__(self):
        return "<User(fullname={}, osf_password={}, osf_local_folder_path={})>".format(
            self.full_name, self.osf_password, self.osf_local_folder_path)



class Node(Base):
    __tablename__ = "node"

    PROJECT = 'project'
    COMPONENT = 'component'



    id = Column(Integer, primary_key=True)
    title = Column(String)
    hash = Column(String)
    category = Column(Enum(PROJECT, COMPONENT))
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    osf_id = Column(String)


    locally_created = Column(Boolean, default=False)
    locally_deleted = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('node.id'))
    child_nodes = relationship(
        "Node",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
    )
    files = relationship(
        "File",
        backref=backref('node'),
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def top_level(self):
        return self.parent is None

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


    @validates('path')
    def validate_path(self, key, path):
        if not self.parent:
            assert self.user.osf_local_folder_path
        return path

    @validates('top_level')
    def validate_top_level(self, key, top_level):
        if top_level:
            assert self.parent is None
        else:
            assert self.parent is not None
        return top_level

    def __repr__(self):
        return "<Node ({}), category={}, title={}, path={}, parent_id={}>".format(
            self.id, self.category, self.title, self.path, self.parent_id
        )


class File(Base):
    __tablename__ = "file"

    FOLDER = 'folder'
    FILE = 'file'

    DEFAULT_PROVIDER = 'osfstorage'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    hash = Column(String)
    type = Column(Enum(FOLDER, FILE), nullable=False)
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    osf_id = Column(String)
    provider = Column(String, default=DEFAULT_PROVIDER)

    # NOTE: this is called path. It is not any type of file/folder path. Think of it just as an id.
    osf_path = Column(String)

    locally_created = Column(Boolean, default=False)
    locally_deleted = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    node_id = Column(Integer, ForeignKey('node.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('file.id'))

    # remote_side=[id] makes it so that when someone calls myFile.parent, we can determine what variable to
    # match myFile.parent_id with. We go through all File's that are not myFile and then match them on their id field
    # to determine which has the same id as myFile.parent_id.
    #
    # Consider remote_side=[rocko]. calling myFile.parent would then query all others Files and check which has a field
    # rocko which matches with myFile.parent_id
    #
    # remote_side is ONLY used with hierarchical relationships such as this.

    files = relationship(
        "File",
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan",
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

    @validates('parent_id')
    def validate_parent_id(self, key, parent_id):
        assert self.parent.node == self.node
        return parent_id

    @validates('node_id')
    def validate_node_id(self, key, node_id):
        if self.parent:
            assert self.parent.node == self.node
        return node_id

    def __repr__(self):
        return "<File ({}), type={}, name={}, path={}, parent_id={}>".format(
            self.id, self.type, self.name, self.path, self.parent
        )



