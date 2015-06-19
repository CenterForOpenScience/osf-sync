#this is the officialish final cell
import requests
# import hashlib
from ProjectTree import ProjectTree
import os
import asyncio



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


local_folder = '/home/himanshu/OSF-Offline/sandbox/OSF_FOLDER/'


# projectpoll = ProjectTree.ProjectTree()
# projectpoll.build_from_directory(os.path.join(local_folder,'poll'))
#
# projectinverse = ProjectTree.ProjectTree()
# projectinverse.build_from_directory(os.path.join(local_folder,'Inverse optimal moderator'))

# import pdb;pdb.set_trace()
user = requests.get('https://staging2.osf.io:443/api/v2/users/?filter[fullname]=Himanshu Ojha').json()['data'][0]
check_osf(user, local_folder)