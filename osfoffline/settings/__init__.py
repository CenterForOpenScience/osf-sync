import logging
import logging.config

from osfoffline.settings.defaults import *  # noqa


logger = logging.getLogger(__name__)

try:
    from osfoffline.settings.local import *  # noqa
except ImportError:
    logger.debug('No local.py found. Using default settings.')

# Ensure that storage directories are created when application starts
for path in (PROJECT_DB_DIR, PROJECT_LOG_DIR):
    logger.info('Ensuring {} exists'.format(path))
    os.makedirs(path, exist_ok=True)

logging.config.dictConfig(LOGGING_CONFIG)
