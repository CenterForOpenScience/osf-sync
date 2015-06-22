__author__ = 'himanshu'
import requests
import os
import asyncio
__author__ = 'himanshu'
import requests
import os
import asyncio
import aiohttp
from queue import Queue, Empty
from datetime import datetime
from threading import Thread
from models import create_session, User, Node, File

class Poll(Thread):
    def __init__(self, db_url, user):
        super().__init__()
        self._keep_running = True
        self.session = create_session(db_url)
        self.user = user
        # self.remote_user = self.get_remote_user()
        # self._waiting_coros = Queue()
        # self._tasks = []
        self._loop = None                           # Loop must be initialized in child thread.
        # self.limit_simultaneous_processes = None    # Semaphore must be initialized after the loop is set.

    def stop(self):
        self._keep_running = False

    def run(self):
        self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.
        asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        # self.limit_simultaneous_processes = asyncio.Semaphore(2)
        remote_user = self.get_remote_user()
        print(remote_user)



        self._loop.run_until_complete(self.check_osf(remote_user, '/home/himanshu/OSF-Offline/dumbdir/OSF', 5))

        # # future = asyncio.Future()
        # asyncio.ensure_future(self.check_osf(remote_user, '/home/himanshu/OSF-Offline/dumbdir/OSF'))
        # # future.add_done_callback(got_result)
        # try:
        #     self._loop.run_forever()
        # finally:
        #     self._loop.close()

    # def submit_coro(self, coro, callback=None):
    #     self._waiting_coros.put((coro, callback))


    def get_remote_user(self):
        # # print('getting remote user')
        # url = 'https://staging2.osf.io:443/api/v2/users/?filter[fullname]={}'.format(self.user.fullname)
        # # print(url)
        # response = yield from aiohttp.request('GET', url)
        # # print('got response')
        # content = yield from response.json()
        # print(content['data'][0])
        # yield content['data'][0]
        return requests.get('https://staging2.osf.io:443/api/v2/users/?filter[fullname]={}'.format(self.user.fullname)).json()['data'][0]

    @asyncio.coroutine
    def check_osf(self,user, recheck_time=None):
        user_id = user['id']
        while self._keep_running:
            remote_projects = requests.get('https://staging2.osf.io:443/api/v2/users/{}/nodes/?filter[category]=project'.format(user_id))
            projects = projects.json()['data']
            for project in projects:
                local_project = self.session.query(Node).filter(Node.guid == project['guid']).find()
                if not local_project:
                    new_project = Node(name=project['name'], guid=project['guid'], category='project')
                    self.session.add(new_project)
                    self.save()
                yield from self.check_component(project)

            #todo: handle projects in local that are not in server. the above for loop does not look at those.
            for project in self._created_projects(projects):
                 print('new project created on server:{}'.format(project.name))

            print('---------SHOULD HAVE ALL OPEN OSF FILES---------')

            if recheck_time:
                print('SLEEPING.................................................................................')
                yield from asyncio.sleep(recheck_time)


    #fixme: logic for check_osf -> check_project -> check_component -> check_file_folders is off




    def _created_projects(self, server_projects):
        local_projects = self.user.projects
        server_project_guids = (project['guid'] for project in server_projects)
        for local in local_projects:
            if local.guid not in server_project_guids: #todo: figure out if I should use guid or nid
                yield local

    #todo: if nothing to do here, then refactor this method out. go directly to check_component
    @asyncio.coroutine
    def check_project(self,project,local_folder):
        # if not os.path.exists(os.path.join(local_folder,project['name'])):
        #     os.makedirs(os.path.join(local_folder, project['name']))
        # todo: stuff to do here before checking project
        # if project['title'] == 'poll':
        #     pt = projectpoll
        # else:
        #     pt = projectinverse
        yield from self.check_component(project, local_folder)

    @asyncio.coroutine
    def check_file_folder(self,file_folder,local_folder):
        if file_folder['item_type']=='folder':
            print('folder!')
            new_local_folder = os.path.join(local_folder, file_folder['name'])
            try:
                folder = requests.get(file_folder['links']['related']).json()['data']
                if not os.path.exists(new_local_folder):
                    os.makedirs(new_local_folder)
                for inner in folder:
                    yield from self.check_file_folder(inner,new_local_folder)
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

    @asyncio.coroutine
    def check_component(self,component, local_folder):

        new_local_folder = os.path.join(local_folder, component['title'])


        if not os.path.exists(new_local_folder):
                os.makedirs(new_local_folder)
        files_folders = requests.get(component['links']['files']['related']).json()['data']
        for file_folder in files_folders:
            yield from self.check_file_folder(file_folder,new_local_folder)
        #todo: handle file_folders in local that are not in server. the above for loop does not look at those.
            # for file_folder in local but not in server:
            #     print('new file_folder created on server!')

        child_components = []
        child_components_resp = requests.get(component['links']['children']['related']).json()
        child_components.extend(child_components_resp['data'])
        while child_components_resp['links']['next'] != None:
            child_components_resp = requests.get(component['links']['next']).json()
            child_components.extend(child_components_resp['data'])
        for child_component in child_components:
            yield from self.check_component(child_component, new_local_folder)


        for created_component in self._created_components(component, child_components):
            print('new component created on server:{}'.format(created_component.name))



    def _created_components(self, parent_component, server_components):
        local_parent_component = self.session.query(Node).filter(Node.guid == parent_component['guid']).first() #todo: nid or guid????
        local_components = local_parent_component.components
        server_component_guids = [component['guid'] for component in server_components]
        for local in local_components:
            if local.guid not in server_component_guids: #todo: figure out if I should use guid or nid
                yield local

    # def _created_file_folders(self, component=None, parent_folder=None):
    #
    #     if parent_folder:
    #         local_parent_component = self.session.query(Node).filter(Node.guid == component['guid']).first()
    #         local_file_folders = local_parent_component.files
    #         server_file_folder
    #     elif component:
    #         pass
    #     else:
    #         raise ValueError

        local_parent_component = self.session.query(Node).filter(Node.guid == parent_component['guid']).first() #todo: nid or guid????
        local_components = local_parent_component.components
        server_component_guids = [component['guid'] for component in server_components]
        for local in local_components:
            if local.guid not in server_component_guids: #todo: figure out if I should use guid or nid
                yield local






    # @asyncio.coroutine
    # def process_coros(self):
    #     while self._keep_running:
    #         try:
    #             while True:
    #                 coro, callback = self._waiting_coros.get_nowait()
    #                 task = asyncio.async(coro())
    #                 if callback:
    #                     task.add_done_callback(callback)
    #                 self._tasks.append(task)
    #         except Empty as e:
    #             pass
    #         yield from asyncio.sleep(3)     # sleep so the other tasks can run


poller = Poll('///temp.db', User(fullname='Himanshu Ojha'))


# class Job(object):
#     def __init__(self, idx):
#         super().__init__()
#         self._idx = idx
#
#     def process(self):
#         background_worker.submit_coro(self._process, self._process_callback)
#
#     @asyncio.coroutine
#     def _process(self):
#         with (yield from background_worker.limit_simultaneous_processes):
#             print("received processing slot %d" % self._idx)
#             start = datetime.now()
#             yield from asyncio.sleep(2)
#             print("processing %d took %s" % (self._idx, str(datetime.now() - start)))
#
#     def _process_callback(self, future):
#         print("callback %d triggered" % self._idx)


def main():
    print("starting worker...")
    poller.start()  #started background thread. background_worker.run() must be called internally.


    command = None
    while command != "quit":
        import time
        time.sleep(1)
        print('1')
        # command = input("enter 'quit' to stop the program: \n")

    print("stopping...")
    poller.stop()
    poller.join()

if __name__=="__main__":
    main()



"""
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
"""