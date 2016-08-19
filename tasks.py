import os
import shutil

from invoke import task, run

from osfsync import settings


def drop_db():
    if os.path.exists(settings.PROJECT_DB_FILE):
        os.remove(settings.PROJECT_DB_FILE)


def drop_log():
    if os.path.exists(settings.PROJECT_LOG_FILE):
        os.remove(settings.PROJECT_LOG_FILE)


@task(aliases=['flake8'])
def flake(ctx):
    run('flake8 osfsync/', echo=True)


@task
def start(ctx):
    from start import start
    start()


@task
def start_for_tests(ctx, dropdb=True, droplog=False, dropdir=False):
    """
    Start the OSF Sync client in a clean configuration suitable for testing

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
def qt_gen(ctx):
    run('pyuic5 ./osfsync/gui/qt/static/login.ui -o ./osfsync/gui/qt/generated/login.py')
    run('pyuic5 ./osfsync/gui/qt/static/preferences.ui -o ./osfsync/gui/qt/generated/preferences.py')
    run('pyrcc5 ./osfsync/gui/qt/static/resources.qrc -o ./osfsync/gui/qt/generated/resources.py')


@task
def wipe(ctx, hard=True):
    if hard:
        drop_db()
        drop_log()
    else:
        print("rm '{0}'".format(settings.PROJECT_DB_FILE))
        print("rm '{0}'".format(settings.PROJECT_LOG_FILE))
