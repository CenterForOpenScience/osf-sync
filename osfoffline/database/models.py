import os
import datetime

from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy import UniqueConstraint
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref, validates

from osfoffline import settings


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(String, primary_key=True)

    folder = Column(String)
    full_name = Column(String, nullable=False)
    login = Column(String, nullable=False)
    oauth_token = Column(String, nullable=False)

    files = relationship('File', backref=backref('user'), cascade='all, delete-orphan')
    nodes = relationship('Node', backref=backref('user'), cascade='all, delete-orphan')

    def __repr__(self):
        return "<User(fullname={}, folder={})>".format(self.full_name, self.folder)


class Node(Base):
    __tablename__ = 'node'

    id = Column(String, primary_key=True)

    sync = Column(Boolean, default=False, nullable=False)
    title = Column(String)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('node.id'), nullable=True)

    children = relationship('Node', backref=backref('parent', remote_side=[id]), cascade='all')
    files = relationship('File', backref=backref('node'), cascade='all, delete-orphan')

    @hybrid_property
    def top_level(self):
        return self.parent is None

    @property
    def path(self):
        """Recursively walk up the path of the node. Top level node joins with the osf folder path of the user
        """
        # +os.path.sep+ instead of os.path.join: http://stackoverflow.com/a/14504695

        name = '{} - {}'.format(self.title, self.id)
        if self.parent:
            return os.path.join(self.parent.path, 'Components', name)
        else:
            return os.path.join(self.user.folder, name)

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
            assert self.user.folder
        return path

    @validates('top_level')
    def validate_top_level(self, key, top_level):
        if top_level:
            assert self.parent is None
        else:
            assert self.parent is not None
        return top_level

    def __repr__(self):
        return '<Node ({}, title={}, path={})>'.format(self.id, self.title, self.path)


class File(Base):
    __tablename__ = "file"
    __table_args__ = (UniqueConstraint('id', 'parent_id', 'name', 'node_id'),)

    FILE = 'file'
    FOLDER = 'folder'

    __id = Column(Integer, primary_key=True)
    id = Column(String)
    name = Column(String)

    md5 = Column(String)
    sha256 = Column(String)

    size = Column(Integer)

    kind = Column(Enum(FOLDER, FILE), nullable=False)
    date_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    provider = Column(String, nullable=False)

    # NOTE: this is called path. It is not any type of file/folder path. Think of it just as an id.
    osf_path = Column(String, nullable=True,
                      default=None)  # todo: unique=True. (can't right now due to duplicates when moved on osf)

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

    children = relationship('File', backref=backref('parent', remote_side=[id]), cascade='all')

    @hybrid_property
    def is_provider(self):
        return (self.parent is None) and (self.is_folder)

    @hybrid_property
    def is_file(self):
        return self.kind == File.FILE

    @hybrid_property
    def is_folder(self):
        return self.kind == File.FOLDER

    @hybrid_property
    def has_parent(self):
        return self.parent is not None

    @property
    def osf_path(self):
        if not self.parent:
            return ''
        return self.id + ((self.is_folder and '/') or '')

    @property
    def path(self):
        """Recursively walk up the path of the file/folder. Top level file/folder joins with the path of the containing node.
        """
        # +os.path.sep+ instead of os.path.join: http://stackoverflow.com/a/14504695
        if self.parent:
            return os.path.join(self.parent.path, self.name) + ('/' if self.is_folder else '')
        else:
            return os.path.join(self.node.path, settings.OSF_STORAGE_FOLDER) + ('/' if self.is_folder else '')

    def locally_create_children(self):
        self.locally_created = True
        if self.is_folder:
            for file_folder in self.files:
                file_folder.locally_create_children()

    @validates('parent_id')
    def validate_parent_id(self, key, parent_id):
        if self.parent:
            assert self.parent.node == self.node
        return parent_id

    @validates('node_id')
    def validate_node_id(self, key, node_id):
        if self.parent:
            assert self.parent.node == self.node
        return node_id

    @validates('files')
    def validate_files(self, key, files):
        if self.is_file:
            assert self.files == []
        return files

    def __repr__(self):
        return '<DBFile({}, {}, {}, {}>'.format(self.id, self.name, self.kind, self.parent_id)
