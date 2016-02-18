import contextlib
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from osfoffline.database.models import Base, User, Node, File
from osfoffline.settings import PROJECT_DB_FILE

CORE_OSFO_MODELS = [User, Node, File]
URL = 'sqlite:///{}'.format(PROJECT_DB_FILE)

engine = create_engine(URL, connect_args={'check_same_thread': False}, )
Base.metadata.create_all(engine)
_session = sessionmaker(bind=engine)()
_session_rlock = threading.RLock()


@contextlib.contextmanager
def Session():
    import threading

    print('locking session - {} : {}'.format(threading.current_thread().ident, threading.current_thread().getName()))
    with _session_rlock:
        print('locking session [acquired] - {} : {}'.format(threading.current_thread().ident, threading.current_thread().getName()))
        yield _session
    print('release session - {} : {}'.format(threading.current_thread().ident, threading.current_thread().getName()))


def drop_db():
    with contextlib.closing(engine.connect()) as con:
        trans = con.begin()
        for table in reversed(Base.metadata.sorted_tables):
            con.execute(table.delete())
        trans.commit()


def clear_models():
    for model in CORE_OSFO_MODELS:
        with Session() as session:
            session.query(model).delete()
