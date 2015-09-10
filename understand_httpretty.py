__author__ = 'himanshu'
import httpretty
import requests
import time
import threading

class TestThread(threading.Thread):

    def run(self):
        while True:
            resp = requests.get('http://www.google.com')
            print(resp)
            try:
                import pdb;pdb.set_trace()
                if resp.json()['BRO'] == 'STOP':
                    break
            except:
                time.sleep(5)



t = TestThread()
t.start()
while True:
    time.sleep(10)