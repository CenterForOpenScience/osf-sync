__author__ = 'himanshu'
import httpretty
import json
import time
from understand_httpretty import TestThread
@httpretty.activate
def test_check_if_thread_is_stopped():
    httpretty.register_uri(
        httpretty.GET,
        'http://www.google.com',
        body=json.dumps({'BRO':'STOP'})
    )

    t = TestThread()
    t.start()

    while True:
        time.sleep(10)

