#usage: workon osfoffline; python test_requests.py
__author__ = 'himanshu'
import httpretty
import requests
import json
import unittest

class TestRequests(unittest.TestCase):


    @httpretty.activate
    def mockResponse(self):
        httpretty.register_uri(httpretty.GET, "http://api.yipit.com/v1/deals/",
                               body='[{"title": "Test Deal"}]',
                               content_type="application/json")

    @mockResponse
    def test_yipit_api_returning_deals(self):

        response = requests.get('http://api.yipit.com/v1/deals/')

        self.assertEqual( response.json(), [{"title": "Test Deal"}])




if __name__=="__main__":
    unittest.main()
