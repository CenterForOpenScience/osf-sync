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


import asyncio
import requests
from pprint import pprint



old_projects = []
old_components = []


# @asyncio.coroutine
def check_projects(user):

    url = 'https://staging2.osf.io/api/v2/users/{}/nodes'.format(user['id'])
#     print(url)
    
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
        old_projects = projects 
    else:
        yield from four_hundred(resp)

# @asyncio.coroutine
def get_components(user):

    url = 'https://staging2.osf.io/api/v2/users/{}/nodes'.format(user['id'])
#     print(url)

    resp = requests.get(url)
    if resp.status_code == 200:
        components = resp.json()['data']
        pprint(resp.json()['data'])
#         pprint(projects)
#         pprint(old_projects)
        if changed(components, old_components):
            print("projects changed.")
        else:
            print("projects are same.")
        old_components = components
    else:
        yield from four_hundred(resp)

def changed(new_list, old_list):
    print(len(new_list), len(old_list))
    return not len(new_list) == len(old_list)


# @asyncio.coroutine
def four_hundred(resp):
    print('---------response is 400---------')
    print(resp.text)



# @asyncio.coroutine
def main_loop(user):
    while True: #why long time versus just True?
        # repeatedly get projects
        projects_changed =  yield from check_projects(user)



        # repeatedly get components of selected project.
        # projects = yield from get_projects(user, projects)


loop = asyncio.get_event_loop()

#assume i have a user with some info.
user = requests.get('https://staging2.osf.io/api/v2/users/?filter[fullname]=Himanshu%20Ojha').json()['data'][0]
# pprint(user)


loop.run_until_complete(main_loop(user))
loop.close()