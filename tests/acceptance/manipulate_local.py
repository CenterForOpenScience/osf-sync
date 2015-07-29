__author__ = 'himanshu'
import unittest
import os

import requests



class Actions(object):
    OSF_FOLDER_LOCATION= ''

    def __init__(self, location):
        self.OSF_FOLDER_LOCATION = location


    def create_local_projects(self, pt_list):
        for pt in pt_list:
            self.create_local_project(pt)

    def create_local_project(self, pt):
        project_location = os.path.join(self.OSF_FOLDER_LOCATION, pt.project.name)
        os.mkdir(project_location)
        self.create_local_folders(pt.project.items, project_location)


    def create_local_folders(self,items, path):
        for item in items:
            if item.kind == Item.FILE:
                self.create_local_file(item, path)
            else:
                os.mkdir(os.path.join(path,item.name))

    def create_local_file(self, item, path):
        file = open(os.path.join(path, item.name), 'w+')
        file.close()

    # def clean(self):
    #     shtils.rmtree(self.OSF_FOLDER_LOCATION)


    #todo: create actions for osf


class TestOSFOffline(unittest.TestCase):

    def setUp(self):
        self.pt1 = ProjectTree()
        self.project1 = Item(kind=Item.PROJECT, name='p1', guid=Item.DEFAULT_GUID, path='', version=0)
        self.component1 = Item(kind=Item.COMPONENT, name='c1', guid=Item.DEFAULT_GUID, path='', version=0)
        self.component2 = Item(kind=Item.COMPONENT, name='c2', guid=Item.DEFAULT_GUID, path='', version=0)
        self.component3 = Item(kind=Item.COMPONENT, name='c3', guid=Item.DEFAULT_GUID, path='', version=0)
        self.pt1.project = self.project1
        self.project1.add_items([self.component1, self.component2, self.component3])
        self.actions = Actions('/home/himanshu/OSF-Offline/dumbdir/OSF/')

        self.user_osf_id = 'p42te'
        self.oauth_token = 'eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ'
        self.headers =  {
            'Authorization' : 'Bearer {}'.format(self.oauth_token)
        }
        self.user_url = 'https://staging2.osf.io/api/v2/users/{}/'.format(self.user_osf_id)

    def test_create_local_project(self):
        self.actions.create_local_projects([self.pt1])
        self.check_in_sync([self.pt1], self.actions.OSF_FOLDER_LOCATION)


    def check_in_sync(self, pt_list, path):
        osf_dir = os.path.join(path, 'OSF')
        self.assertTrue(os.path.isdir(osf_dir))
        user = requests.get(self.user_url, headers=self.headers)
        projects = requests.get(user['links']['nodes']['relation'], headers=self.headers)
        temp = []
        for remote in projects:
            if remote['category'] == 'project':
                temp.append(remote)
        projects = temp

        for pt in pt_list:
            project = self.get_desired_remote_node(pt.project, projects)
            self.check_node_in_sync(pt.project, osf_dir, projects)

    def get_desired_remote_node(self, local, nodes):
        for node in nodes:
            if node['title'] == local.name:
                    return node
        return None

    def check_node_in_sync(self, node,path, remote_nodes):
        node_dir = os.path.join(path, node.name)
        self.assertEquals(len(node.items), )
        self.assertTrue(os.isdir(node_dir))



        for child in node.items:
            if child.kind ==
