# Just to insure requirement
import colorlog  # noqa

# Development mode: use a local OSF dev version and more granular logging
DEV_MODE = False  # TODO (abought): auto-set flag when using `inv start_for_tests`

# General settings
PROJECT_NAME = 'osf-offline'
PROJECT_AUTHOR = 'cos'
APPLICATION_SCOPES = 'osf.full_write'

# Base URL for API server; used to fetch data
API_BASE = 'https://test-api.osf.io'
FILE_BASE = 'https://test-files.osf.io'

# Interval (in seconds) to poll the OSF for server-side file changes
POLL_DELAY = 24 * 60 * 60  # Once per day

# Time to keep alert messages on screen (in milliseconds); may not be configurable on all platforms
ALERT_TIME = 1000  # ms

LOG_LEVEL = 'INFO'

# Logging configuration
CONSOLE_FORMATTER = {
    '()': 'colorlog.ColoredFormatter',
    'format': '%(cyan)s[%(asctime)s]%(log_color)s[%(threadName)s][%(filename)s][%(levelname)s][%(name)s]: %(reset)s%(message)s'
}

FILE_FORMATTER = '[%(asctime)s][%(threadName)s][%(filename)s][%(levelname)s][%(name)s]: %(message)s'

IGNORED_NAMES = ['.DS_Store', 'lost+found', 'Desktop.ini']

OSF_STORAGE_FOLDER = 'OSF Storage'

# wab~,vmc,vhd,vo1,vo2,vsv,vud,vmdk,vmsn,vmsd,hdd,vdi,vmwarevm,nvram,vmx,vmem,iso,dmg,sparseimage,wim,ost,o,qtch,log
# wab~,vmc,vhd,vdi,vo1,vo2,vsv,vud,iso,dmg,sparseimage,sys,cab,exe,msi,dll,dl_,wim,ost,o,qtch,log,ithmb,vmdk,vmem,vmsd,vmsn,vmss,vmx,vmxf,menudata,appicon,appinfo,pva,pvs,pvi,pvm,fdd,hds,drk,mem,nvram,hdd
