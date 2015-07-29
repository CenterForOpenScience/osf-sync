
# usage: nosetests /path/to/manipulate_osf.py -x


from osfoffline.polling_osf_manager.api_url_builder import wb_file_url, wb_move_url
import os
import json
import requests
import time
from unittest import TestCase

osf_path = '/home/himanshu/Desktop/OSF/'
osfstorage_path = os.path.join(osf_path, 'new_test_project','osfstorage')
user_id = '5bqt9'
nid1 = 'dz5mg'
# nid2 = ''
headers = {'Authorization':'Bearer {}'.format(user_id)}
session = requests.Session()
session.headers.update(headers)


def create_osf_folder(folder_name, nid, parent=None):
    if parent:
        path = parent['path'] + folder_name
    else:
        path = '/{}'.format(folder_name)
    params = {
        'path': path,
        'provider': 'osfstorage',
        'nid': nid
    }
    files_url = wb_file_url()
    resp = session.post(files_url,params=params)
    print(resp.content)
    assert resp.ok
    return resp.json()

def create_osf_file(file_name, nid, parent=None):
    if parent:
        path = parent['path'] + file_name
    else:
        path = '/{}'.format(file_name)
    params = {
        'path': path,
        'provider': 'osfstorage',
        'nid': nid
    }
    files_url = wb_file_url()
    path_to_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files',file_name)
    file = open(path_to_file, 'rb')
    resp = session.put(files_url, params=params, data=file)
    assert resp.ok
    return resp.json()

def rename_osf_file_folder(rename_to, path, nid, parent=None):
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
            'path': parent['path'] if parent else '/',
            'provider': 'osfstorage',
            'nid': nid
        }
    }

    resp = session.post(url, data=json.dumps(data))
    assert resp.ok
    return resp.json()

def update_osf_file(file,new_content_file_name, nid,parent=None):
    if parent:
        path = parent['path'] + file['name']
    else:
        path = '/{}'.format(file['name'])
    params = {
        'path': path,
        'provider': 'osfstorage',
        'nid': nid
    }
    files_url = wb_file_url()
    path_to_file_with_new_content = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', new_content_file_name)
    content = open(path_to_file_with_new_content, 'rb')
    resp = session.put(files_url, params=params, data=content)
    assert resp.ok
    return resp.json()

def move_osf_file_folder(file_folder_to_move, nid, folder_to_move_under=None):
    url = wb_move_url()
    data = {
        'rename': file_folder_to_move['name'],
        'conflict': 'replace',
        'source': {
            'path': file_folder_to_move['path'],
            'provider': 'osfstorage',
            'nid': nid
        },
        'destination': {
            'path': folder_to_move_under['path'] if folder_to_move_under else '/',
            'provider': 'osfstorage',
            'nid': nid
        }
    }

    resp = session.post(url, data=json.dumps(data))
    assert resp.ok
    return resp.json()



def delete_osf_file_folder(file_folder, nid):
    # http://localhost:7777/file?path=/&nid=dz5mg&provider=osfstorage
    url = wb_file_url(path=file_folder['path'],nid=nid,provider='osfstorage')
    resp = session.delete(url)
    resp.close()



def build_path(*args):
    return os.path.join(osfstorage_path, *args)

# usage: nosetests /path/to/manipulate_osf.py -x



class TestFail(Exception):
    pass

def assertTrue(func, arg):
    """
    checks for condition every 5 seconds. If eventually True then good. else TestFail
    """
    for i in range(10):
        if func(arg):
            return
        else:
            time.sleep(5)
    raise TestFail

def assertFalse(func, arg):
    """
    checks for condition every 5 seconds. If eventually False then good. else TestFail
    """
    for i in range(10):
        if not func(arg):
            return
        else:
            time.sleep(5)
    raise TestFail


def test_create_folder():
    folder = create_osf_folder('folder1', nid1)
    assertTrue(os.path.isdir, build_path('folder1') )

    delete_osf_file_folder(folder, nid1)
    assertFalse(os.path.exists, build_path('folder1'))

def test_create_file():
    file = create_osf_file('file1', nid1)
    assertTrue(os.path.isfile, build_path('file1'))

    delete_osf_file_folder(file, nid1)
    assertFalse(os.path.exists, build_path('file1'))

def test_create_nested_folders_with_same_name():
    folder1 = create_osf_folder('folder', nid1)
    assertTrue(os.path.isdir, build_path('folder') )

    folder1_1 = create_osf_folder('folder', nid1, folder1)
    assertTrue(os.path.isdir, build_path('folder','folder'))

    folder1_1_1 = create_osf_folder('folder', nid1, folder1_1)
    assertTrue(os.path.isdir, build_path('folder','folder','folder'))

    delete_osf_file_folder(folder1, nid1)
    assertFalse(os.path.exists, build_path('folder'))

def test_create_nested_file():
    folder1 = create_osf_folder('folder1', nid1)
    assertTrue(os.path.isdir, build_path('folder1') )

    file = create_osf_file('file1', nid1, folder1)
    assertTrue(os.path.isfile, build_path('folder1','file1'))

    folder1_1 = create_osf_folder('folder1.1', nid1, folder1)
    assertTrue(os.path.isdir, build_path('folder1', 'folder1.1'))

    file2 = create_osf_file('file2', nid1, folder1_1)
    assertTrue(os.path.isfile, build_path('folder1','folder1.1','file2'))

    delete_osf_file_folder(folder1, nid1)
    assertFalse(os.path.exists, build_path('folder1'))

#fails
# def test_file_folder_with_same_name():
#     file = create_osf_folder('file1', nid1)
#     assertTrue(os.path.isdir, build_path('file1'))
#
#     folder=create_osf_file('file1', nid1)
#     assertTrue(os.path.isfile, build_path('file1'))
#
#     delete_osf_file_folder(file, nid1)
#     delete_osf_file_folder(folder, nid1)
#     assertFalse(os.path.exists, build_path('file1'))


def test_nested_file_with_same_name_as_containing_folder():
    folder = create_osf_folder('file1', nid1)
    assertTrue(os.path.isdir, build_path('file1'))

    create_osf_file('file1', nid1, folder)
    assertTrue(os.path.isfile, build_path('file1','file1'))

    delete_osf_file_folder(folder,nid1)
    assertFalse(os.path.exists, build_path('file1'))

def test_renaming_folder():
    folder = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    rename_osf_file_folder('f2', folder['path'], nid1)
    assertTrue(os.path.isdir, build_path('f2'))

    delete_osf_file_folder(folder,nid1)
    assertFalse(os.path.exists, build_path('f2'))
    assertFalse(os.path.exists, build_path('f1'))

def test_renaming_folder_with_stuff_in_it():
    folder = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    subfolder = create_osf_folder('ff1', nid1, folder)
    assertTrue(os.path.isdir, build_path('f1','ff1'))

    subfile = create_osf_file('file2', nid1, folder)
    assertTrue(os.path.isfile, build_path('f1','file2'))

    rename_osf_file_folder('f2', folder['path'], nid1)
    assertTrue(os.path.isdir, build_path('f2'))
    assertTrue(os.path.isdir, build_path('f2','ff1'))
    assertTrue(os.path.isdir, build_path('f2','file2'))


    delete_osf_file_folder(folder,nid1)
    assertFalse(os.path.exists, build_path('f2'))


def test_rename_file():
    file = create_osf_file('file1',nid1)
    assertTrue(os.path.isfile, build_path('file1'))

    rename_osf_file_folder('renamed_file', file['path'], nid1)
    assertTrue(os.path.isfile, build_path('renamed_file'))

    delete_osf_file_folder(file,nid1)
    assertFalse(os.path.exists, build_path('renamed_file'))


def test_update_file():
    file = create_osf_file('file1', nid1)
    assertTrue(os.path.isfile, build_path('file1'))

    should_be_contents = open(build_path('NEWCONTENTS'),'r+').read()
    update_osf_file(file,'NEWCONTENTS', nid1)
    def same_contents(should_be_contents):
        new_contents = open(build_path('file1'),'r+').read()
        return new_contents == should_be_contents
    assertTrue(same_contents, should_be_contents)

    delete_osf_file_folder(file,nid1)
    assertFalse(os.path.exists, build_path('file1'))

def test_update_nested_file():
    folder = create_osf_folder('myfolder', nid1)
    assertTrue(os.path.isdir, build_path('myfolder'))

    file = create_osf_file('file1', nid1, folder)
    assertTrue(os.path.isfile, build_path('myfolder','file1'))

    path_to_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files','NEWCONTENTS')
    should_be_contents = open(path_to_file,'r+').read()
    update_osf_file(file,'NEWCONTENTS', nid1)
    def same_contents(should_be_contents):
        new_contents = open(build_path('myfolder','file1'),'r+').read()
        return new_contents == should_be_contents
    assertTrue(same_contents, should_be_contents)

    delete_osf_file_folder(folder,nid1)
    assertFalse(os.path.exists, build_path('myfolder'))


def test_move_file_from_top_to_folder():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    file = create_osf_file('file1', nid1)
    assertTrue(os.path.isfile, build_path('file1'))

    move_osf_file_folder(file, nid1, folder1)
    assertTrue(os.path.isfile, build_path('f1','file1'))
    assertFalse(os.path.exists, build_path('file1'))

    delete_osf_file_folder(folder1,nid1)
    assertFalse(os.path.exists, build_path('f1'))

def test_move_file_from_folder1_to_folder2():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    file = create_osf_file('file1', nid1, folder1)
    assertTrue(os.path.isfile, build_path('f1','file1'))

    folder2 = create_osf_folder('f2', nid1)
    assertTrue(os.path.isdir, build_path('f2'))

    move_osf_file_folder(file,nid1, folder2 )
    assertTrue(os.path.isfile, build_path('f2','file1'))
    assertFalse(os.path.exists, build_path('f1','file1'))

    delete_osf_file_folder(folder1,nid1)
    assertFalse(os.path.exists, build_path('f1'))

    delete_osf_file_folder(folder2,nid1)
    assertFalse(os.path.exists, build_path('f2'))

def test_move_folder1_under_folder2():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    folder2 = create_osf_folder('f2', nid1)
    assertTrue(os.path.isdir, build_path('f2'))

    move_osf_file_folder(folder1,nid1, folder2 )
    assertTrue(os.path.isfile, build_path('f2','file1'))
    assertFalse(os.path.exists, build_path('f1','file1'))

    delete_osf_file_folder(folder1,nid1)
    assertFalse(os.path.exists, build_path('f1'))

def test_move_folder1_with_stuff_in_it_under_folder2():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    afolder = create_osf_folder('afolder',nid1, folder1)
    assertTrue(os.path.isdir, build_path('f1','afolder'))

    afile = create_osf_file('file2',nid1, folder1)
    assertTrue(os.path.isfile, build_path('f1','file2'))


    folder2 = create_osf_folder('f2', nid1)
    assertTrue(os.path.isdir, build_path('f2'))

    move_osf_file_folder(folder1,nid1, folder2 )
    assertTrue(os.path.isdir, build_path('f2','f1'))
    assertTrue(os.path.isdir, build_path('f2','f1','afolder'))
    assertTrue(os.path.isfile, build_path('f2','f1','file2'))
    assertFalse(os.path.exists, build_path('f1'))

    delete_osf_file_folder(folder2, nid1)
    assertFalse(os.path.exists, build_path('f2'))


def test_move_folder1_under_folder2_with_stuff_in_it():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))


    folder2 = create_osf_folder('f2', nid1)
    assertTrue(os.path.isdir, build_path('f2'))

    afolder = create_osf_folder('afolder',nid1, folder2)
    assertTrue(os.path.isdir, build_path('f2','afolder'))

    afile = create_osf_file('file2',nid1, folder2)
    assertTrue(os.path.isfile, build_path('f2','file2'))


    move_osf_file_folder(folder1,nid1, folder2 )
    assertTrue(os.path.isdir, build_path('f2','f1'))
    assertTrue(os.path.isdir, build_path('f2','afolder'))
    assertTrue(os.path.isfile, build_path('f2','file2'))
    assertFalse(os.path.exists, build_path('f1'))

    delete_osf_file_folder(folder2,nid1)
    assertFalse(os.path.exists, build_path('f2'))

def test_move_folder1_with_stuff_under_folder2_with_stuff():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    folder2 = create_osf_folder('f2', nid1)
    assertTrue(os.path.isdir, build_path('f2'))

    junkfolder1 = create_osf_folder('junkfolder1',nid1, folder1)
    assertTrue(os.path.isdir, build_path('f1','junkfolder1'))

    junkfile1 = create_osf_file('file1',nid1, folder1)
    assertTrue(os.path.isfile, build_path('f1','file1'))

    junkfolder2 = create_osf_folder('junkfolder2',nid1, folder2)
    assertTrue(os.path.isdir, build_path('f2','junkfolder2'))

    junkfile2 = create_osf_file('file2',nid1, folder2)
    assertTrue(os.path.isfile, build_path('f2','file2'))

    move_osf_file_folder(folder1,nid1, folder2 )
    assertTrue(os.path.isdir, build_path('f2','f1'))
    assertTrue(os.path.isdir, build_path('f2','junkfolder2'))
    assertTrue(os.path.isfile, build_path('f2','file2'))
    assertTrue(os.path.isdir, build_path('f2', 'f1','junkfolder1'))
    assertTrue(os.path.isfile, build_path('f2', 'f1','file1'))
    assertFalse(os.path.exists, build_path('f1'))

    delete_osf_file_folder(folder2,nid1)
    assertFalse(os.path.exists, build_path('f2'))


def test_move_folder_to_toplevel():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    folder1_1 = create_osf_folder('f1.1', nid1, folder1)
    assertTrue(os.path.isdir, build_path('f1','f1.1'))

    move_osf_file_folder(folder1_1, nid1)
    assertTrue(os.path.isdir, build_path('f1'))
    assertTrue(os.path.isdir, build_path('f1.1'))
    assertFalse(os.path.exists, build_path('f1','f1.1'))

    delete_osf_file_folder(folder1,nid1)
    assertFalse(os.path.exists, build_path('f1'))

    delete_osf_file_folder(folder1_1,nid1)
    assertFalse(os.path.exists, build_path('f1.1'))

def test_move_folder_with_stuff_in_it_to_toplevel():
    folder1 = create_osf_folder('f1', nid1)
    assertTrue(os.path.isdir, build_path('f1'))

    folder1_1 = create_osf_folder('f1.1', nid1, folder1)
    assertTrue(os.path.isdir, build_path('f1','f1.1'))

    folder1_1_junk = create_osf_folder('junk', nid1, folder1_1)
    assertTrue(os.path.isdir, build_path('f1','f1.1','junk'))

    file1_1_junk = create_osf_file('file1', nid1, folder1_1)
    assertTrue(os.path.isfile, build_path('f1','f1.1','file1'))

    move_osf_file_folder(folder1_1, nid1)
    assertTrue(os.path.isdir, build_path('f1'))
    assertTrue(os.path.isdir, build_path('f1.1'))
    assertFalse(os.path.exists, build_path('f1','f1.1'))
    assertTrue(os.path.isdir, build_path('f1.1','junk'))
    assertTrue(os.path.isfile, build_path('f1.1','file1'))

    delete_osf_file_folder(folder1,nid1)
    assertFalse(os.path.exists, build_path('f1'))

    delete_osf_file_folder(folder1_1,nid1)
    assertFalse(os.path.exists, build_path('f1.1'))

def test_move_file_to_toplevel():
    folder1 = create_osf_folder('myfolder', nid1)
    assertTrue(os.path.isdir, build_path('myfolder'))

    file = create_osf_file('file1', nid1, folder1)
    assertTrue(os.path.isdir, build_path('myfolder','file1'))

    move_osf_file_folder(file, nid1)
    assertTrue(os.path.isdir, build_path('myfolder'))
    assertTrue(os.path.isdir, build_path('file1'))
    assertFalse(os.path.exists, build_path('myfolder','file1'))

    delete_osf_file_folder(folder1,nid1)
    assertFalse(os.path.exists, build_path('myfolder'))

    delete_osf_file_folder(file,nid1)
    assertFalse(os.path.exists, build_path('file1'))























# def test():
#     # create online
#     #create folder1
#     folder1 = create_osf_folder('folder1', nid1)
#     time.sleep(5)
#     assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder1'))
#
#     #create file1 in folder1
#     file1 = create_osf_file('file1', nid1, folder1['path'])
#     time.sleep(10)
#     assert os.path.isfile(os.path.join(osf_path, 'new_test_project','osfstorage','folder1','file1'))
#
#     #create folder2
#     folder2 = create_osf_folder('folder2', nid1)
#     time.sleep(10)
#     assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2'))
#
#     #create file2
#     file2 = create_osf_file('file2', nid1)
#     time.sleep(10)
#     assert os.path.isfile(os.path.join(osf_path, 'new_test_project','osfstorage','file2'))
#
#     #create folder2.1
#     folder2_1 = create_osf_folder('folder2.1', nid1, folder2['path'])
#     time.sleep(10)
#     assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1'))
#
#     #create folder2.1.1
#     folder2_1_1 = create_osf_folder('folder2.1.1', nid1, folder2_1['path'])
#     time.sleep(10)
#     assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1','folder2.1.1'))
#
#
#     #rename file2 to file2RENAMED
#     file2RENAMED = rename_osf_file_folder('file2RENAMED', file2['path'], nid1, '/' )
#     time.sleep(20)
#     assert os.path.isfile(os.path.join(osf_path, 'new_test_project','osfstorage','file2RENAMED'))
#
#     #rename folder2.1.1 to folder2.1.1RENAMED
#     folder_2_1_1RENAMED = rename_osf_file_folder('folder2.1.1RENAMED',folder2_1_1['path'], nid1, folder2_1['path'])
#     time.sleep(20)
#     assert os.path.isdir(os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1','folder2.1.1RENAMED'))
#
#
#     # update file2RENAMED contents
#     new_content_file_name = 'NEWCONTENTS'
#     update_osf_file(file2RENAMED, new_content_file_name, nid1)
#     path_to_file2RENAMED = os.path.join(osf_path, 'new_test_project','osfstorage','file2RENAMED')
#     time.sleep(30)
#     path_to_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files',new_content_file_name)
#     new_contents = open(path_to_file,'r+').read()
#     file2RENAMED_contents = open(path_to_file2RENAMED, 'r+').read()
#     assert new_contents == file2RENAMED_contents
#
#
#     # move file1 to folder2
#     move_osf_file_folder(file1, nid1,folder2)
#     time.sleep(30)
#     old_path = os.path.join(osf_path, 'new_test_project','osfstorage','folder1','file1')
#     path = os.path.join(osf_path, 'new_test_project','osfstorage','folder2','file1')
#     assert os.path.exists(old_path) is False
#     assert os.path.isfile(path)
#
#     # move folder2.1.1RENAMED to folder2
#     move_osf_file_folder(folder_2_1_1RENAMED, nid1,folder2)
#     time.sleep(30)
#     old_path = os.path.join(osf_path, 'new_test_project','osfstorage','folder1','folder2.1','folder2.1.1')
#     path = os.path.join(osf_path, 'new_test_project','osfstorage','folder2','folder2.1.1RENAMED')
#     assert os.path.exists(old_path) is False
#     assert os.path.isdir(path)
#
#     # move folder2 to folder1
#     move_osf_file_folder(folder2, nid1, folder1)
#     time.sleep(60)
#     old_path = os.path.join(osf_path, 'new_test_project','osfstorage','folder2')
#     path = os.path.join(osf_path, 'new_test_project','osfstorage','folder1','folder2')
#     assert os.path.exists(old_path) is False
#     assert os.path.isdir(path)
#
#     # clear osfstorage for nid1
#
#     #delete file2
#     delete_osf_file_folder(file2RENAMED, nid1)
#     time.sleep(30)
#     path = os.path.join(osf_path, 'new_test_project','osfstorage','file2RENAMED')
#     assert os.path.exists(path) is False
#
#
#     #delete folder1
#     delete_osf_file_folder(folder1, nid1)
#     time.sleep(20)
#     path = os.path.join(osf_path, 'new_test_project','osfstorage','folder1')
#     assert os.path.exists(path) is False
#
#     #delete folder2
#     delete_osf_file_folder(folder2, nid1)
#     time.sleep(20)
#     path = os.path.join(osf_path, 'new_test_project','osfstorage','folder2')
#     assert os.path.exists(path) is False



