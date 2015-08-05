__author__ = 'himanshu'
from PyQt5.QtWidgets import QSystemTrayIcon
from queue import Queue
from datetime import datetime, timedelta

show_alerts = True

DOWNLOAD = 0
UPLOAD = 1
MODIFYING = 2
DELETING = 3
MOVING = 4

ALERT_TIME = 1000


alert_icon = None

last_alert_time = None
alert_queue = Queue()



def setup_alerts(system_tray_icon):
    global alert_icon
    global show_alerts

    alert_icon = system_tray_icon
    if not alert_icon.supportsMessages():
        show_alerts = False


def alert_running():
    global last_alert_time
    cur_time = datetime.now()

    if not last_alert_time:
        return False
    return cur_time - last_alert_time < timedelta(milliseconds=ALERT_TIME)


def run_alert(alert_title, alert_message):
    alert_icon.showMessage(
                alert_title,
                alert_message,
                QSystemTrayIcon.NoIcon,
                msecs=ALERT_TIME  # fixme: currently, I have NO control over duration of alert. I think this is only for linux... hopefully.
    )

    global last_alert_time
    last_alert_time = datetime.now()

def clear_queue():
    # clear the queue in a thread safe manner.
    with alert_queue.mutex:
        alert_queue.queue.clear()


def warn(message):
    global show_alerts

    if (alert_icon is None) or (not show_alerts):
        return
    else:
        if alert_icon.supportsMessages():
            run_alert("Problems Syncing", message)

def info(file_name, action):
    global show_alerts
    global last_alert_time

    if (alert_icon is None) or (not show_alerts):
        return
    else:
        title = {
            DOWNLOAD: "Downloading",
            UPLOAD: "Uploading",
            MODIFYING: "Modifying",
            DELETING: "Deleting",
        }

        text = "{} {}".format(title[action], file_name)
        alert_tuple = (text, "- OSF Offline")
        if alert_icon.supportsMessages():
            """Idea is that if there is an alert already running, we will IGNORE the new alert.
               Don't want to queue them up and run them one by one because a queued alert could be outdated.
               Don't want to give a 'updating x files' alert because
            """
            if alert_running():
                alert_queue.put_nowait(alert_tuple)
            else:
                if alert_queue.empty():
                    run_alert(alert_tuple[0], alert_tuple[1])
                elif datetime.now() - last_alert_time < timedelta(milliseconds= (ALERT_TIME * 3)) :  # last alert was recent
                    run_alert('Updating {} files'.format(alert_queue.qsize() + 1), "Check <a href='www.osf.io'>www.osf.io</a> for details.")
                    clear_queue()
                else:
                    run_alert(alert_tuple[0], alert_tuple[1])
                    clear_queue()

        else:
            show_alerts = False