#usage: workon osfoffline; python test_requests.py
__author__ = 'himanshu'
import httpretty
import requests
import json
import unittest
from osfoffline.polling_osf_manager.api_url_builder import api_user_url
# from tests.fixtures.factories.osf.factories import UserFactory
from osfoffline.settings import API_BASE, WB_BASE
from osfoffline.polling_osf_manager.remote_objects import RemoteUser
from tests.fixtures.mock_responses.logged_in.user import get_user_response
class TestRequests(unittest.TestCase):


    # @httpretty.activate
    # def mockResponse(self):
    #     httpretty.register_uri(httpretty.GET, "http://api.yipit.com/v1/deals/",
    #                            body='[{"title": "Test Deal"}]',
    #                            content_type="application/json")
    #
    # @mockResponse
    # def test_yipit_api_returning_deals(self):
    #
    #     response = requests.get('http://api.yipit.com/v1/deals/')
    #
    #     self.assertEqual( response.json(), [{"title": "Test Deal"}])

    @httpretty.activate
    def test_work(self):
        httpretty.register_uri(
            httpretty.GET,
            api_user_url('1'),
            body=get_user_response('1', 'himanshu'),
            content_type="application/json"
        )

        response = requests.get(api_user_url('1')).json()['data']
        user = RemoteUser(response)

        self.assertEqual( user.id, '1' )



if __name__=="__main__":
    unittest.main()
