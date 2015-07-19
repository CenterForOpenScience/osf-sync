__author__ = 'himanshu'
from osfoffline.models import setup_db, get_session, User, Node, File
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
import factory
from appdirs import user_data_dir

setup_db(user_data_dir('test-app', 'test-author'))
session = get_session()

# class User(Base):
#     """ A SQLAlchemy simple model class who represents a user """
#     __tablename__ = 'UserTable'
#
#     id = Column(Integer(), primary_key=True)
#     name = Column(Unicode(20))
#
# Base.metadata.create_all(engine)



class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = session   # the SQLAlchemy session object

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: u'User %d' % n)