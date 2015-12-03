import contextlib

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from osfoffline.database.models import Base, User, Node, File
from osfoffline.settings import PROJECT_DB_FILE


CORE_OSFO_MODELS = [User, Node, File]
URL = 'sqlite:///{}'.format(PROJECT_DB_FILE)

# sqlite+pysqlcipher://:passphrase/file_path
# URL = 'sqlite+pysqlcipher://:PASSWORD/{DB_FILE_PATH}'.format(DB_FILE_PATH=DB_FILE_PATH)

engine = create_engine(
    URL,
    # poolclass=SingletonThreadPool,
    connect_args={'check_same_thread': False},
)
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

session = Session()


def drop_db():
    with contextlib.closing(engine.connect()) as con:
        trans = con.begin()
        for table in reversed(Base.metadata.sorted_tables):
            con.execute(table.delete())
        trans.commit()


def clear_models():
    for model in CORE_OSFO_MODELS:
        session.query(model).delete()
