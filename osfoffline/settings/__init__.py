from osfoffline.utils.path import ensure_folders

from .app_settings import ALERT_TIME, API_BASE, DB_FILE_PATH, FILE_BASE, PROJECT_DB_PATH, DEV_MODE, POLL_DELAY
from .log_config import PROJECT_LOG_PATH

# Ensure that storage directories are created when application starts
ensure_folders(PROJECT_DB_PATH)
ensure_folders(PROJECT_LOG_PATH)
