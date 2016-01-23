import os

from osfoffline import settings

# override the default database name when running tests
settings.PROJECT_DB_FILE = os.path.join(settings.PROJECT_DB_DIR, 'test.db')
