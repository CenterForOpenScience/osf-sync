__author__ = 'himanshu'

from unittest import TestCase
import requests
from osfoffline.polling_osf_manager.api_url_builder import api_user_url
from osfoffline.polling_osf_manager.remote_objects import RemoteFile,RemoteFileFolder,RemoteObject,RemoteFolder,RemoteNode,RemoteUser
from osfoffline.polling_osf_manager.osf_query import OSFQuery
import asyncio
from tests.utils.decorators import async
class TestRemoteObjects(TestCase):

    def setUp(self):
        # fixme: currently this is static. Need to make this work in general. ONCE you have a mock response thing working.
        self.user_id = '5bqt9'
        self._loop = asyncio.new_event_loop()
        self.osf_query = OSFQuery(self._loop, self.user_id)

    # @async
    # def test_get_all_paginated_users(self):
    #     self.osf_query._get_all_paginated_members()



