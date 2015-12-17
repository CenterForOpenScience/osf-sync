from invoke import task, run


@task(aliases=['flake8'])
def flake():
    run('flake8 osfoffline/', echo=True)


@task
def start():
    from start import start
    start()


@task
def qt_gen():
    run('pyuic5 ./osfoffline/gui/qt/static/login.ui -o ./osfoffline/gui/qt/generated/login.py')
    run('pyuic5 ./osfoffline/gui/qt/static/preferences.ui -o ./osfoffline/gui/qt/generated/preferences.py')
    run('pyrcc5 ./osfoffline/gui/qt/static/resources.qrc -o ./osfoffline/gui/qt/generated/resources.py')
