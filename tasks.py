import os
import shutil

from invoke import task, run

from osfoffline import settings


def drop_db():
    if os.path.exists(settings.PROJECT_DB_FILE):
        os.remove(settings.PROJECT_DB_FILE)

def drop_log():
    if os.path.exists(settings.PROJECT_LOG_FILE):
        os.remove(settings.PROJECT_LOG_FILE)

@task(aliases=['flake8'])
def flake():
    run('flake8 osfoffline/', echo=True)


@task
def start():
    from start import start
    start()


@task
def start_for_tests(dropdb=True, droplog=False, dropdir=False):
    """
    Start the OSF offline client in a clean configuration suitable for testing

    :param bool dropdb: Whether to delete the database. Defaults to True
    :param bool droplog: Whether to delete pre-existing shared error log. Defaults to False.
    :param bool dropdir: Whether to delete user data folder (a particular location for testing). Defaults to False.
    """
    if dropdb:
        drop_db()
    if droplog:
        drop_log()

    osf_dir = os.path.expanduser('~/Desktop/OSF')
    if dropdir and os.path.exists(osf_dir):
        shutil.rmtree(osf_dir)

    start()


@task
def qt_gen():
    run('pyuic5 ./osfoffline/gui/qt/static/login.ui -o ./osfoffline/gui/qt/generated/login.py')
    run('pyuic5 ./osfoffline/gui/qt/static/preferences.ui -o ./osfoffline/gui/qt/generated/preferences.py')
    run('pyrcc5 ./osfoffline/gui/qt/static/resources.qrc -o ./osfoffline/gui/qt/generated/resources.py')

@task
def wipe(hard=True):
    if hard:
        drop_db()
        drop_log()
    else:
        print("rm -r '{0}'".format(settings.PROJECT_DB_FILE))
        print("rm -r '{0}'".format(settings.PROJECT_LOG_FILE))
