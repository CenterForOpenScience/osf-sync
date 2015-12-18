# Sample settings file tracking items to be changed for deployment

LOG_LEVEL = 'INFO'

# Specify a Sentry DSN for logging. Do not commit key to github.
SENTRY_DSN = None


## Base URL for API server; used to fetch data
#OSF_URL = 'https://test.osf.io'
#API_BASE = 'https://test-api.osf.io'
#FILE_BASE = 'https://test-files.osf.io'

# Interval (in seconds) to poll the OSF for server-side file changes
REMOTE_CHECK_INTERVAL = 60 * 5  # Every 5 minutes
