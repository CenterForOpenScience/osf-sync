import os

from appdirs import user_data_dir
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from osfoffline.database_manager.models import Base
from osfoffline.settings import PROJECT_NAME, PROJECT_AUTHOR

DB_DIR = user_data_dir(PROJECT_NAME, PROJECT_AUTHOR)
DB_FILE_PATH = os.path.join(DB_DIR, 'osf.db')
URL = 'sqlite:///{}'.format(DB_FILE_PATH)

# sqlite+pysqlcipher://:passphrase/file_path
# URL = 'sqlite+pysqlcipher://:PASSWORD/{DB_FILE_PATH}'.format(DB_FILE_PATH=DB_FILE_PATH)

if not os.path.isdir(DB_DIR):
    os.makedirs(DB_DIR)
engine = create_engine(
    URL,
    # poolclass=SingletonThreadPool,
    connect_args={'check_same_thread': False},
)
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

session = Session()
