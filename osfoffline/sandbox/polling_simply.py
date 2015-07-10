__author__ = 'himanshu'
import requests
import os
# files = requests.get(myproject['links']['files']['related']) #has both folders and files


def download_file(file_link, download_to):
    r = requests.get(file_link)
    with open(download_to, 'wb') as fd:
        for chunk in r.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference for client.
            fd.write(chunk)
        print('file SHOULD now be on local storage.')

def download_folder(file_folder, download_to):
    if file_folder['item_type']=='folder':
        print('folder!')
        folder = requests.get(file_folder['links']['related']).json()['data']
        if not os.path.exists(file_folder['name']):
            os.makedirs(os.path.join(download_to, file_folder['name']))
        for inner in folder:
            download_folder(inner, os.path.join(download_to,inner['name']))
    elif file_folder['item_type'] == 'file':
        print('file!')
        download_file(file_folder['links']['self'], os.path.join(download_to, file_folder['name']))




def check_file_folder(file_folder):
    if file_folder['item_type']=='folder':
        print('folder!')
        folder = requests.get(file_folder['links']['related']).json()['data']
        for inner in folder:
            check_file_folder(inner)
    elif file_folder['item_type']=='file':
        print('file!')
        download_file(file_folder['links']['self'], '/home/himanshu/OSF-Offline/sandbox/osfstorage/{}'.format(file_folder['name']))




def check_component(component):
    files_folders = requests.get(component['links']['files']['related']).json()['data']
    for file_folder in files_folders:
        check_file_folder(file_folder)
    print(file_folder)

    child_components = []
    child_components_resp = requests.get(component['links']['children']['related']).json()
    child_components.extend(child_components_resp['data'])
    while child_components_resp['links']['meta']['next'] != None:
        child_components_resp = requests.get(component['links']['next']).json()
        child_components.extend(child_components_resp['data'])
    for child_component in child_components:
        check_component(child_component)


