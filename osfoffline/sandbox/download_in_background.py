__author__ = 'himanshu'
import requests
import os
import asyncio

from queue import Queue, Empty
from datetime import datetime
from threading import Thread


class BackgroundWorker(Thread):
    def __init__(self):
        super().__init__()
        self._keep_running = True
        self._waiting_coros = Queue()
        self._tasks = []
        self._loop = None                           # Loop must be initialized in child thread.
        self.limit_simultaneous_processes = None    # Semaphore must be initialized after the loop is set.

    def stop(self):
        self._keep_running = False

    def run(self):
        self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.
        asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        self.limit_simultaneous_processes = asyncio.Semaphore(2)
        self._loop.run_until_complete(self.process_coros())

    def submit_coro(self, coro, callback=None):
        self._waiting_coros.put((coro, callback))

    @asyncio.coroutine
    def process_coros(self):
        while self._keep_running:
            try:
                while True:
                    coro, callback = self._waiting_coros.get_nowait()
                    task = asyncio.async(coro())
                    if callback:
                        task.add_done_callback(callback)
                    self._tasks.append(task)
            except Empty as e:
                pass
            yield from asyncio.sleep(3)     # sleep so the other tasks can run


background_worker = BackgroundWorker()


class Job(object):
    def __init__(self, idx):
        super().__init__()
        self._idx = idx

    def process(self):
        background_worker.submit_coro(self._process, self._process_callback)

    @asyncio.coroutine
    def _process(self):
        with (yield from background_worker.limit_simultaneous_processes):
            print("received processing slot %d" % self._idx)
            start = datetime.now()
            yield from asyncio.sleep(2)
            print("processing %d took %s" % (self._idx, str(datetime.now() - start)))

    def _process_callback(self, future):
        print("callback %d triggered" % self._idx)


def check_osf(user, local_folder):
    user_id = user['id']
    projects = requests.get('https://staging2.osf.io:443/api/v2/users/{}/nodes/?filter[category]=project'.format(user_id))
    projects = projects.json()['data']
    for project in projects:
        check_project(project,local_folder)
    print('---------SHOULD HAVE ALL OPEN OSF FILES---------')

def check_project(project,local_folder):
    # if not os.path.exists(os.path.join(local_folder,project['name'])):
    #     os.makedirs(os.path.join(local_folder, project['name']))
    # todo: stuff to do here before checking project
    # if project['title'] == 'poll':
    #     pt = projectpoll
    # else:
    #     pt = projectinverse
    check_component(project, local_folder)

def check_file_folder(file_folder,local_folder):
    if file_folder['item_type']=='folder':
        print('folder!')
        new_local_folder = os.path.join(local_folder, file_folder['name'])
        try:
            folder = requests.get(file_folder['links']['related']).json()['data']
            if not os.path.exists(new_local_folder):
                os.makedirs(new_local_folder)
            for inner in folder:
                check_file_folder(inner,new_local_folder)
        except TypeError:
            print('request for check_file_folder failed because folder is not accessible to us.')
            print('can debug if you want using the link: {}'.format(file_folder['links']['related']))

    elif file_folder['item_type']=='file':
        print('file!')
        new_local_file_path = os.path.join(local_folder,file_folder['name'])
        if not os.path.exists(new_local_file_path):
            r = requests.get(file_folder['links']['self'])
            with open(new_local_file_path, 'wb') as fd:
                for chunk in r.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                    fd.write(chunk)
                print('file SHOULD now be on local storage.')

def check_component(component, local_folder):
    new_local_folder = os.path.join(local_folder, component['title'])
    if not os.path.exists(new_local_folder):
            os.makedirs(new_local_folder)
    files_folders = requests.get(component['links']['files']['related']).json()['data']
    for file_folder in files_folders:
        check_file_folder(file_folder,new_local_folder)

    child_components = []
    child_components_resp = requests.get(component['links']['children']['related']).json()
    child_components.extend(child_components_resp['data'])
    while child_components_resp['links']['next'] != None:
        child_components_resp = requests.get(component['links']['next']).json()
        child_components.extend(child_components_resp['data'])
    for child_component in child_components:
        check_component(child_component, new_local_folder)


def get_remote_user(user):
    return requests.get('https://staging2.osf.io:443/api/v2/users/?filter[fullname]={}'.format(user.fullname)).json()['data'][0]

def main():
    print("starting worker...")
    background_worker.start()  #started background thread. background_worker.run() must be called internally.

    for idx in range(10):
        download_job = Job(idx)
        download_job.process()

    command = None
    while command != "quit":
        command = input("enter 'quit' to stop the program: \n")

    print("stopping...")
    background_worker.stop()
    background_worker.join()

if __name__=="__main__":
    main()