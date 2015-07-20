__author__ = 'himanshu'
from osfoffline.models import setup_db, get_session, User, Node, File
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from factory.alchemy import SQLAlchemyModelFactory
from factory import Sequence
from tests.fixtures.factories.common import session

# class User(Base):
#     """ A SQLAlchemy simple model class who represents a user """
#     __tablename__ = 'UserTable'
#
#     id = Column(Integer(), primary_key=True)
#     name = Column(Unicode(20))
#
# Base.metadata.create_all(engine)

session = session

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = session   # the SQLAlchemy session object

    id = Sequence(lambda n: n)
    full_name = Sequence(lambda n: u'User %d' % n)
    osf_login = Sequence(lambda n: u'osf_login %d' % n)
    osf_password = Sequence(lambda n: u'osf_password %d' % n)
    oauth_token = Sequence(lambda n: u'oauth_token %d' % n)
    osf_id = Sequence(lambda n: u'osf_id %d' % n)

    logged_in = False
