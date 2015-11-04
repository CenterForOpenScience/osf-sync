import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from osfoffline.database_manager.models import Base
from osfoffline.settings import DB_FILE_PATH, PROJECT_DB_PATH


URL = 'sqlite:///{}'.format(DB_FILE_PATH)

# sqlite+pysqlcipher://:passphrase/file_path
# URL = 'sqlite+pysqlcipher://:PASSWORD/{DB_FILE_PATH}'.format(DB_FILE_PATH=DB_FILE_PATH)

if not os.path.isdir(PROJECT_DB_PATH):
    os.makedirs(PROJECT_DB_PATH)

engine = create_engine(
    URL,
    # poolclass=SingletonThreadPool,
    connect_args={'check_same_thread': False},
)
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

session = Session()
