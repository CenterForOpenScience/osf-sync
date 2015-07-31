__author__ = 'himanshu'
import unittest
import os
import shutil
import requests
import time
from tests.utils.url_builder import api_node_files, wb_file_url
from osfoffline.polling_osf_manager.remote_objects import RemoteFile, RemoteFolder, RemoteFileFolder, dict_to_remote_object
osf_path = '/home/himanshu/Desktop/OSF/'
osfstorage_path = os.path.join(osf_path, 'new_test_project','osfstorage')
user_id = '5bqt9'
nid1 = 'dz5mg'
# nid2 = ''
headers = {'Authorization':'Bearer {}'.format(user_id)}
session = requests.Session()
session.headers.update(headers)


def create_local(*args, is_dir=True):
    if is_dir:
        os.makedirs(build_path(*args))
    else:
        dirs = args[:-1]
        os.makedirs(build_path(dirs))
        path = build_path(*args)
        file = open(path, 'w+')
        file.write('some text')
        file.close()


def build_path(*args):
    return os.path.join(osfstorage_path, *args)




# usage: nosetests /path/to/manipulate_osf.py -x



class TestFail(Exception):
    pass


def teardown(self):
    shutil.rmtree(osfstorage_path)
    for i in range(10):
        file_folders = get_node_file_folders(nid1)
        if len(file_folders)==0:
            return
    assert TestFail


def get_node_file_folders(node_id):
    node_files_url = api_node_files(node_id)
    resp = session.get(node_files_url)
    assert resp.ok
    osf_storage_folder = RemoteFolder(resp.json()['data'][0])
    assert osf_storage_folder.provider == osf_storage_folder.name
    children_resp = session.get(osf_storage_folder.child_files_url)
    assert children_resp.ok
    return [dict_to_remote_object(file_folder) for file_folder in children_resp.json()['data']]

def get_children_file_folders(parent_folder):
    assert isinstance(parent_folder, RemoteFolder)
    url = parent_folder.child_files_url
    resp = session.get(url)
    assert resp.ok
    return [dict_to_remote_object(file_folder) for file_folder in resp.json()['data']]



def file_in_list(file_name, remote_object_list):
    for remote_object in remote_object_list:
        if isinstance(remote_object, RemoteFile) and remote_object.name == file_name:
            return True
    return False

def folder_in_list(folder_name, remote_object_list):
    for remote_object in remote_object_list:
        if isinstance(remote_object, RemoteFolder) and remote_object.name == folder_name:
            return True
    return False


def assert_contains_file(file_name, nid, parent_folder=None):
    if parent_folder:
        for i in range(10):
            children = get_children_file_folders(parent_folder)
            if file_in_list(file_name, children):
                return
            time.sleep(5)
        assert TestFail

    for i in range(10):
        file_folders = get_node_file_folders(nid)
        if file_in_list(file_name,file_folders):
            return
        time.sleep(5)
    assert TestFail

def assert_contains_folder(folder_name, nid, parent_folder=None):
    if parent_folder:
        for i in range(10):
            children = get_children_file_folders(parent_folder)
            if folder_in_list(folder_name, children):
                return
            time.sleep(5)
        assert TestFail
    for i in range(10):
        file_folders = get_node_file_folders(nid)
        if folder_in_list(folder_name,file_folders):
            return
        time.sleep(5)
    assert TestFail


def test_create_local_folder():
    create_local_folder('new_folder')
    assert_contains_folder('new_folder', nid1)

def test_create_local_file():
    create_local_file('new_file')
    assert_contains_file('new_file', nid1)

def test_create_local_nested_folders():
    create_local_folder('f')
    assert_contains_folder('f', nid1)

    create_local_folder('a', build_path('f'))
    assert_contains_folder('a', nid1, )




    # def test_create_local_project(self):
    #     self.actions.create_local_projects([self.pt1])
    #     self.check_in_sync([self.pt1], self.actions.OSF_FOLDER_LOCATION)
    #
    #
    # def check_in_sync(self, pt_list, path):
    #     osf_dir = os.path.join(path, 'OSF')
    #     self.assertTrue(os.path.isdir(osf_dir))
    #     user = requests.get(self.user_url, headers=self.headers)
    #     projects = requests.get(user['links']['nodes']['relation'], headers=self.headers)
    #     temp = []
    #     for remote in projects:
    #         if remote['category'] == 'project':
    #             temp.append(remote)
    #     projects = temp
    #
    #     for pt in pt_list:
    #         project = self.get_desired_remote_node(pt.project, projects)
    #         self.check_node_in_sync(pt.project, osf_dir, projects)
    #
    # def get_desired_remote_node(self, local, nodes):
    #     for node in nodes:
    #         if node['title'] == local.name:
    #                 return node
    #     return None
    #
    # def check_node_in_sync(self, node,path, remote_nodes):
    #     node_dir = os.path.join(path, node.name)
    #     self.assertEquals(len(node.items), )
    #     self.assertTrue(os.isdir(node_dir))
    #
    #
    #
    #     for child in node.items:
    #         if child.kind ==
