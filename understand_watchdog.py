from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer
import time
import logging
logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
observer = Observer()  # create observer. watched for events on files.
observer.schedule(LoggingEventHandler(), "/home/himanshu/Desktop/OSF", recursive=True)
observer.start()
try:
    while True:
       time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()