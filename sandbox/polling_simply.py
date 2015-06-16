__author__ = 'himanshu'
import requests
def check_component(component):
    files_folders = requests.get(component['links']['files']['related']).json()['data']
    for file_folder in files_folders:
        if file_folder['item_type']=='folder':
            print('folder!')
        elif file_folder['item_type']=='file':
            print('file!')
        print(file_folder)

