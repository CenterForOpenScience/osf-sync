# Running tests:

1) Make sure pytest is installed: `pip install -r requirements.txt`
2) Use `py.test` to run the test suite (PyCharm has a run configuration for this also)

*) If you want increased verbosity use `py.test -v`
*) If you need to access the program's stdout (for ipdb, print statements, etc), use `py.test -s`
*) To run a specific suite or test use: `py.test tests/<module>.py::<TestClassName>::(<test_name>)?`
