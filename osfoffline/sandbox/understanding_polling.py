#example using loop.call_soon
# import asyncio
#
# def hello_world(loop):
#     print('Hello World')
#     loop.stop()
#
# loop = asyncio.get_event_loop()
#
# # Schedule a call to hello_world()
# loop.call_soon(hello_world, loop)
#
# # Blocking call interrupted by loop.stop()
# loop.run_forever()
# loop.close()

#example using coroutine
# import asyncio
# import datetime
#
# @asyncio.coroutine
# def display_date(loop):
#     end_time = loop.time() + 5.0
#     while True:
#         print(datetime.datetime.now())
#         if (loop.time() + 1.0) >= end_time:
#             break
#         yield from asyncio.sleep(1)
#
# loop = asyncio.get_event_loop()
# # Blocking call which returns when the display_date() coroutine is done
# loop.run_until_complete(display_date(loop))
# loop.close()



#what we want: poll the api for changes

#requirements:
    # get heartbeat NO NEED
    # get projects
    # keep calling get projects
    # when a project is created or deleted, send alert. in this case, send just print to screen
    # get current components of a project
    # keep calling get components for a specific project
    # when a component is created or deleted, send alert. in this case, send just print to screen

#note, this is polling. NOT long-polling

import asyncio
import requests
from pprint import pprint


old_projects = []
old_components = []

@asyncio.coroutine
def handle_project_changes(user):

    url = user['links']['nodes']['relation']
    print(url)
    
    resp = requests.get(url)
    if resp.status_code == 200:
        projects = resp.json()['data']
        # pprint(resp.json()['data'])
#         pprint(projects)
#         pprint(old_projects)
        if changed(projects, old_projects):
            print("projects changed.")
        else:
            print("projects are same.")
        old_projects.clear()
        old_projects.extend(projects)


        for project in projects:
            yield from check_components(user, project)

    else:
        yield from four_hundred(resp)


@asyncio.coroutine
def check_changes(component):
    #todo: check current component details with what is on FileStructure

    #check children
    url = 'https://staging2.osf.io/api/v2/nodes/{}/children'.format(user['id'])
#     print(url)
    resp = requests.get(url)
    if resp.status_code == 200:
        children = resp.json()['data']

        pprint(resp.json()['data'])
#         pprint(projects)
#         pprint(old_projects)
        if changed(components, old_components):
            print("components changed.")
        else:
            print("components are same.")
        old_components.clear()
        old_components.extend(components)
    else:
        yield from four_hundred(resp)



def changed(new_list, old_list):
    print(len(new_list), len(old_list))
    return not len(new_list) == len(old_list)


@asyncio.coroutine
def four_hundred(resp):
    print('---------response is 400---------')
    print(resp.text)



@asyncio.coroutine
def main_loop(user):
    while True: #why long time versus just True?
        # repeatedly get projects
        yield from handle_project_changes(user)


        # repeatedly get components of selected project.
        # projects = yield from get_projects(user, projects)


loop = asyncio.get_event_loop()

#assume i have a user with some info.
user = requests.get('https://staging2.osf.io/api/v2/users/?filter[fullname]=Himanshu%20Ojha').json()['data'][0]
# pprint(user)


loop.run_until_complete(main_loop(user))
loop.close()