__author__ = 'himanshu'

import sqlite3
import sqlalchemy

from sqlalchemy import create_engine, Table, ForeignKey, Enum
from datetime import date
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import Column, Integer, Boolean, String, Date
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy_mptt.mixins import BaseNestedSets



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
engine = create_engine('sqlite:///example.db', echo=False)
Base = declarative_base()






class User(Base):
     __tablename__ = 'user'

     id = Column(Integer, primary_key=True)
     name = Column(String)
     osf_login = Column(String)
     osf_password = Column(String)
     osf_path = Column(String)
     oauth_token = Column(String)
     projects = relationship("Node")

     def __repr__(self):
       return "<User(name={}, osf_password={}, osf_path={})>".format(
                             self.name, self.osf_password, self.osf_path)

#todo: can have it so that all nodes and subnodes know that they are part of the same user.
#todo: http://docs.sqlalchemy.org/en/rel_1_0/orm/self_referential.html#composite-adjacency-lists
class Node(Base):
    __tablename__ = "node"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    guid = Column(String)
    hash = Column(String)
    category = Column(Enum('project', 'component'))
    nid = Column(String) # todo: GUID versus NID
    # date_modified = Column(date) # todo: date versus datetime, again. :(

    user_id = Column(Integer, ForeignKey('user.id'))
    parent_id = Column(Integer, ForeignKey('node.id'))
    components = relationship("Node",
                backref=backref('parent', remote_side=[id])
            )
    files = relationship("File")

    def __repr__(self):
        return "<Node ({}), category={}, name={}, path={}, parent_id={}>".format(
            self.id, self.category, self.name, self.path, self.parent_id
        )


#todo: can have it so that all files and folders know that they are part of the same component.
#todo: http://docs.sqlalchemy.org/en/rel_1_0/orm/self_referential.html#composite-adjacency-lists
class File(Base):
    __tablename__ = "file"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    guid = Column(String)
    hash = Column(String)
    type = Column(Enum('file','folder'))
    # date_modified = Column(date) #todo: date versus datetime, again. :(

    node_id = Column(Integer, ForeignKey('node.id'))
    parent_id = Column(Integer, ForeignKey('file.id'))
    files = relationship("File",
                backref=backref('parent', remote_side=[id])
            )

    def __repr__(self):
        return "<File ({}), type={}, name={}, path={}, parent_id={}>".format(
            self.id, self.type, self.name, self.path, self.parent_id
        )


Base.metadata.create_all(engine)


Session = sessionmaker()
Session.configure(bind=engine)
session = Session()


# user = User(name="Himanshu")
#
# project = Node(category="project", name="test project 1")
# user.projects.append(project)
#
# project = Node(category="project", name="test project 2")
# component1 = Node(category="component", name="component 1", parent_id=project.id)
# project.components.append(component1)
#
#
# user.projects.append(project)
#
# session.add(user)
# session.commit()
#
# for instance in session.query(User):
#     print(instance)
# for instance in session.query(Node).filter():
#     print(instance)
#

user =session.query(User).filter(User.name == "Himanshu").all()[0]
user.osf_path="/this/is/a/path"
session.commit()
himanshu = session.query(User).filter(User.name == "Himanshu").all()
print(himanshu)


############################################
# association_table = Table('association', Base.metadata,
#     Column('left_id', Integer, ForeignKey('left.id')),
#     Column('right_id', Integer, ForeignKey('right.id'))
# )
#
# class Parent(Base):
#     __tablename__ = 'left'
#     id = Column(Integer, primary_key=True)
#     children = relationship("Child",
#                     secondary=association_table,
#                     backref="parents")
#
# class Child(Base):
#     __tablename__ = 'right'
#     id = Column(Integer, primary_key=True)


#
#
# user = User(name='himanshu')
# user.name = 'max'
# user.name = 'sam'
# user.name = 'sandman'
# Session = sessionmaker()
# Session.configure(bind=engine)
# session = Session()
# # user.save()
# print(session.dirty)
# print(session.new)
# session.add(user)
# print(session.dirty)
# print(session.new)
# session.commit()
# for instance in session.query(User):
#     print(instance.name)


# class Item(Base):
#     __tablename = 'Item'
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     path = Column(String)
#     guid = Column(String)
#     hash = Column(String)
#     # kind = Column()  from set
#     # items = Column()
#     version = Column(Integer)


# class Project(Base):
#     __tablename = 'Project'
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     path = Column(String)
#     guid = Column(String)
#     hash = Column(String)
#     date_modified = Column(date) #todo: date versus datetime, again. :(
#     files = #todo: how to map. #todo: backref
#     components =
#
# class Component(Base):
#     __tablename = 'Component'
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     path = Column(String)
#     guid = Column(String)
#     hash = Column(String)
#     date_modified = Column(date) #todo: date versus datetime, again. :(
#     files = #todo: how to map. #todo: backref
#     components
#
#
# class Folder(Base):
#     __tablename = 'Folder'
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     path = Column(String)
#     guid = Column(String)
#     hash = Column(String)
#     date_modified = Column(date) #todo: date versus datetime, again. :(
#     files = #todo: how to map. #todo: backref
#
#
# class File(Base):
#     __tablename = 'Component'
#
# class File(Base):
#     __tablename__ = 'File'
#
#
#
