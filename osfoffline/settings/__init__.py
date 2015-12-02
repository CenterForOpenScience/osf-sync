import logging
import logging.config

from osfoffline.settings.defaults import *  # noqa
from osfoffline.utils.path import ensure_folders


logger = logging.getLogger(__name__)

try:
    from osfoffline.settings.local import *  # noqa
except ImportError:
    logger.warning('No local.py found. Using default settings.')

# Ensure that storage directories are created when application starts
for path in (PROJECT_DB_DIR, PROJECT_LOG_DIR):
    logger.info('Ensuring {} exists'.format(path))
    ensure_folders(path)

logging.config.dictConfig(LOGGING_CONFIG)
