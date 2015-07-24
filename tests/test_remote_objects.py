__author__ = 'himanshu'
from unittest import TestCase
import requests
from osfoffline.polling_osf_manager.api_url_builder import api_user_url
from osfoffline.polling_osf_manager.remote_objects import RemoteFile,RemoteFileFolder,RemoteObject,RemoteFolder,RemoteNode,RemoteUser

class TestRemoteObjects(TestCase):

    def setUp(self):
        # fixme: currently this is static. Need to make this work in general. ONCE you have a mock response thing working.
        self.user_id = '5bqt9'
        self.headers = {'Authorization':'Bearer {}'.format(self.user_id)}
        self.user_resp = requests.get(api_user_url(self.user_id), headers=self.headers).json()['data']
        self.node_resp = requests.get(self.user_resp['links']['nodes']['relation'], headers=self.headers).json()['data'][0]

        self.folder_provider_resp = requests.get(self.node_resp['links']['files']['related'], headers=self.headers).json()['data'][0]
        print(self.folder_provider_resp)
        self.folder_resp =requests.get(self.folder_provider_resp['links']['related'], headers=self.headers).json()['data'][1]
        self.file_resp = requests.get(self.folder_resp['links']['related'], headers=self.headers).json()['data'][0]

    def test_object(self):
        RemoteObject(self.user_resp)
        RemoteObject(self.node_resp)
        RemoteObject(self.folder_provider_resp)
        RemoteObject(self.folder_resp)
        RemoteObject(self.file_resp)

    def test_user(self):
        RemoteUser(self.user_resp)

    def test_node(self):
        RemoteNode(self.node_resp)

    def test_file_folder(self):
        RemoteFileFolder(self.folder_provider_resp)
        RemoteFileFolder(self.folder_resp)
        RemoteFileFolder(self.file_resp)

    def test_file(self):
        RemoteFile(self.file_resp)

    def test_folder(self):
        RemoteFolder(self.folder_provider_resp)
        RemoteFolder(self.folder_resp)