import shutil
import os
from appdirs import user_data_dir
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool
from osfoffline.database_manager.models import Base
from osfoffline.settings import PROJECT_NAME, PROJECT_AUTHOR


class DB(object):

    DB_DIR = user_data_dir(PROJECT_NAME, PROJECT_AUTHOR)
    DB_FILE_PATH = os.path.join(DB_DIR, 'osf.db')
    URL = 'sqlite:///{}'.format(DB_FILE_PATH)

    Session = None

    @classmethod
    def setup_db(cls, db_dir=None):
        if db_dir:
            cls.DB_DIR = db_dir
            cls.DB_FILE_PATH = os.path.join(cls.DB_DIR, 'osf.db')
            # sqlite+pysqlcipher://:passphrase/file_path
            # URL = 'sqlite+pysqlcipher://:PASSWORD/{DB_FILE_PATH}'.format(DB_FILE_PATH=DB_FILE_PATH)
            cls.URL = 'sqlite:///{}'.format(cls.DB_FILE_PATH)

        cls.create_models()
        cls.create_session()

    @classmethod
    def remove_db(cls):
        shutil.rmtree(cls.DB_DIR)

    @classmethod
    def get_session(cls):
        if cls.Session:
            return cls.Session()
        else:
            raise ValueError

    @classmethod
    def create_models(cls):
        """ Create sql alchemy engine and models for all file systems.
        """
        if not os.path.isdir(cls.DB_DIR):
            os.makedirs(cls.DB_DIR)
        engine = create_engine(
            cls.URL,
            poolclass=SingletonThreadPool,
            connect_args={'check_same_thread': False},
        )
        Base.metadata.create_all(engine)

    @classmethod
    def create_session(cls):
        """
        this function sets up the Session global variable using the previously setup db.
        The Session object in this case uses the identity map pattern.
        There is a single Session map. Whenever we create a new session via get_session(),
        we are really just getting the currently stored session in that thread.
        Session object here refers to getting a db session from a map from identity map pattern ma
        :return:
        """

        # for this application, should only lead to 2 connections in total
        engine = create_engine(cls.URL, echo=False)
        session_factory = sessionmaker(bind=engine)


        cls.Session = scoped_session(session_factory)



