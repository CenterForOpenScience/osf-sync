import shutil
import logging

from contextlib import contextmanager

from osfoffline.database import session
from osfoffline import settings


def save(session, *items_to_save):
    for item in items_to_save:
        session.add(item)
    try:
        session.commit()
    except:
        logging.exception('Error saving to the database')
        session.rollback()
        raise


# @contextmanager
# def session_scope():
#     """Provide a transactional scope around a series of operations."""
#     try:
#         yield session
#         session.commit()
#     except:
#         session.rollback()
#         raise
#     finally:
#         session.close()


def remove_db():
    shutil.rmtree(settings.PROJECT_DB_DIR)
