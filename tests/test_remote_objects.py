__author__ = 'himanshu'
from unittest import TestCase
import requests

class TestRemoteObjects(TestCase):

    def setUp(self):
        self.headers = {'Authorization':'Bearer {}'}

