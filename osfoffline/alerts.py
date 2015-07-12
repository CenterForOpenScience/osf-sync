__author__ = 'himanshu'
from PyQt5.QtWidgets import QSystemTrayIcon

DOWNLOAD = 0
UPLOAD = 1
MODIFYING = 2
DELETING = 3

alert_icon = None
# icon = QSystemTrayIcon.MessageIcon()


def setup_alerts(system_tray_icon):
    global alert_icon
    alert_icon = system_tray_icon


def info(file_name, action):
    global alert_icon
    # global icon
    if alert_icon is None:
        return
    else:
        title = {
            DOWNLOAD: "Downloading",
            UPLOAD: "Uploading",
            MODIFYING: "Modifying",
            DELETING: "Deleting",
        }

        text = "{} {}".format(title[action], file_name)
        alert_icon.showMessage(
            text,
            "      - OSF Offline",  # todo: there is some way to format strings in pyqt. how again?
            QSystemTrayIcon.NoIcon,
            1000  # fixme: currently, I have NO control over duration of alert.
        )

# if __name__=="__main__":
# app = QApplication(sys.argv)
#
#     if not QSystemTrayIcon.isSystemTrayAvailable():
#         QMessageBox.critical(None, "Systray",
#                 "Could not detect a system tray on this system")
#         sys.exit(1)
#
#     QApplication.setQuitOnLastWindowClosed(False)
#     dialog = QDialog()
#     setup_alerts(dialog)
#     info('hi',DOWNLOAD)
#
#     app.exec_()
