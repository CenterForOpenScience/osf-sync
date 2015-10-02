from invoke import task, run
import os
# WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')


# @task
# def wheelhouse(develop=False):
#     req_file = 'dev-requirements.txt' if develop else 'requirements.txt'
#     cmd = 'pip wheel --find-links={} -r {} --wheel-dir={}'.format(WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH)
#     run(cmd, pty=True)


# @task
# def install(develop=False, upgrade=False):
#     run('python setup.py develop')
#     req_file = 'dev-requirements.txt' if develop else 'requirements.txt'
#     cmd = 'pip install -r {}'.format(req_file)
#
#     if upgrade:
#         cmd += ' --upgrade'
#     if WHEELHOUSE_PATH:
#         cmd += ' --no-index --find-links={}'.format(WHEELHOUSE_PATH)
#     run(cmd, pty=True)


@task
def flake():
    run('flake8 . --config=./setup.cfg', pty=True)


# @task
# def test(verbose=False):
#     flake()
#     cmd = 'py.test --cov-report term-missing --cov waterbutler tests'
#     if verbose:
#         cmd += ' -v'
#     run(cmd, pty=True)


@task
def start():
    from start import start
    start()

@task
def mock_osf_api_server():
    from tests.fixtures.mock_osf_api_server.osf import app
    app.run(debug=True)


@task
def reset_mock_osf_api_server():
    os.remove('./tests/fixtures/mock_osf_api_server/db_dir/mock_osf_api.db')