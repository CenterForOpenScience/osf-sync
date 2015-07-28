from osfoffline.polling_osf_manager.api_url_builder import wb_file_url, wb_move_url
import os
import json
import requests
import time

osf_path = '/home/himanshu/Desktop/OSF/'
user_id = '5bqt9'
nid1 = 'dz5mg'
# nid2 = ''
headers = {'Authorization':'Bearer {}'.format(user_id)}

def create_osf_folder(folder_name, nid, parent_path=None):
    if parent_path:
        path = parent_path + folder_name
    else:
        path = '/{}'.format(folder_name)
    params = {
        'path': path,
        'provider': 'osfstorage',
        'nid': nid
    }
    files_url = wb_file_url()
    resp = requests.post(files_url,params=params, headers=headers)
    print(resp.content)
    assert resp.ok
    return resp.json()

def create_osf_file(file_name, nid, parent_path=None):
    if parent_path:
        path = parent_path + file_name
    else:
        path = '/{}'.format(file_name)
    params = {
        'path': path,
        'provider': 'osfstorage',
        'nid': nid1
    }
    files_url = wb_file_url()
    path_to_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files',file_name)
    file = open(path_to_file, 'rb')
    resp = requests.put(files_url, params=params, data=file, headers=headers)
    assert resp.ok
    return resp.json()

def rename_osf_file_folder(rename_to, path, parent_path, nid):
    url = wb_move_url()
    data = {
        'rename': rename_to,
        'conflict': 'replace',
        'source': {
            'path': path,
            'provider': 'osfstorage',
            'nid': nid
        },
        'destination': {
            'path': parent_path,
            'provider': 'osfstorage',
            'nid': nid
        }
    }

    resp = requests.post(url, headers=headers, data=json.dumps(data))
    assert resp.ok
    return resp.json()

def update_osf_file():
    pass
def move_osf_folder():
    pass
def move_osf_file():
    pass

def delete_osf_file_folder(file_folder, nid):
    # http://localhost:7777/file?path=/&nid=dz5mg&provider=osfstorage
    url = wb_file_url(path=file_folder['path'],nid=nid,provider='osfstorage')
    resp = requests.delete(url, headers=headers)
    resp.close()


def create_local_file():
    pass
def create_local_folder():
    pass


def assertRaises(exc_class, func, *args):
    try:
        print(*args)
        func(*args)
        assert False
    except exc_class:
        assert True


def test():
    # create online
    #create folder1
    folder1 = create_osf_folder('folder1', nid1)
    time.sleep(5)
    assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder1'))

    #create file1 in folder1
    file1 = create_osf_file('file1', nid1, folder1['path'])
    time.sleep(10)
    assert os.path.isfile(os.path.join(osf_path, 'new_test_project','osfstorage','folder1','file1'))

    #create folder2
    folder2 = create_osf_folder('folder2', nid1)
    time.sleep(10)
    assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2'))

    #create file2
    file2 = create_osf_file('file2', nid1)
    time.sleep(10)
    assert os.path.isfile(os.path.join(osf_path, 'new_test_project','osfstorage','file2'))

    #create folder2.1
    folder2_1 = create_osf_folder('folder2.1', nid1, folder2['path'])
    time.sleep(10)
    assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1'))

    #create folder2.1.1
    folder2_1_1 = create_osf_folder('folder2.1.1', nid1, folder2_1['path'])
    time.sleep(10)
    assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1','folder2.1.1'))


    #rename file2 to file2RENAMED
    rename_osf_file_folder('file2RENAMED', file2['path'], '/', nid1)
    time.sleep(20)
    assert os.path.isfile(os.path.join(osf_path, 'new_test_project','osfstorage','file2RENAMED'))

    #rename folder2.1.1 to folder2.1.1RENAMED
    rename_osf_file_folder('folder2.1.1RENAMED',folder2_1_1['path'], folder2_1['path'], nid1)
    time.sleep(20)
    assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1','folder2.1.1RENAMED'))




    # clear osfstorage for nid1

    #delete file2
    delete_osf_file_folder(file2, nid1)
    time.sleep(30)
    path = os.path.join(osf_path, 'new_test_project','osfstorage','file2RENAMED')
    assert os.path.exists(path) is False


    #delete folder1
    delete_osf_file_folder(folder1, nid1)
    time.sleep(20)
    path = os.path.join(osf_path, 'new_test_project','osfstorage','folder1')
    assert os.path.exists(path) is False

    #delete folder2
    delete_osf_file_folder(folder2, nid1)
    time.sleep(20)
    path = os.path.join(osf_path, 'new_test_project','osfstorage','folder2')
    assert os.path.exists(path) is False



if __name__=="__main__":
    test()










