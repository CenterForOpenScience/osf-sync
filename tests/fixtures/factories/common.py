from appdirs import user_data_dir
from osfoffline.models import setup_db, get_session

setup_db(user_data_dir('test-app', 'test-author'))
session = get_session()
