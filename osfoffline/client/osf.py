"""APIv2 client library for interacting with the OSF API"""

import abc
import iso8601
import threading

import requests

from osfoffline import settings
from osfoffline.utils import Singleton
from osfoffline.utils.authentication import get_current_user


class OSFClient(metaclass=Singleton):

    def __init__(self, limit=5):
        self.user = get_current_user()
        self.headers = {
            'Authorization': 'Bearer {}'.format(self.user.oauth_token),
        }
        self.throttler = threading.Semaphore(limit)
        self.request_session = requests.Session()
        self.request_session.headers.update(self.headers)

    def get_node(self, id):
        return Node.load(self.request_session, id)

    def get_user(self, id='me'):
        return User.load(self.request_session, id)

    def request(self, *args, **kwargs):
        return self.request_session.request(*args, **kwargs)


class BaseResource(abc.ABC):

    OSF_HOST = settings.API_BASE
    API_PREFIX = settings.API_VERSION
    BASE_URL = '{}/{}'.format(OSF_HOST, API_PREFIX)

    def __init__(self, request_session, data):
        self.request_session = request_session
        self.__dict__.update(data['attributes'])
        self.id = data['id']
        self.type = data['type']
        self.raw = data

    @classmethod
    def get_url(cls, *args):
        return cls.BASE_URL

    @classmethod
    def load(cls, request_session, *args):
        resp = request_session.get(cls.get_url(*args), params={'page[size]': 250})
        data = resp.json()

        if isinstance(data['data'], list):
            l = data['data']
            while data['links'].get('next'):
                resp = request_session.get(data['links']['next'], params={'page[size]': 250})
                data = resp.json()
                l.extend(data['data'])
            return [cls(request_session, item) for item in l]
        return cls(request_session, data['data'])


class User(BaseResource):
    """Fetch API data relevant to a specific user"""
    RESOURCE = 'users'

    # def __init__(self, request_session, data):
    #     super().__init__(request_session, data)
    #     self.date_created = iso8601.parse_date(self.date_created)
    #     self.date_modified = iso8601.parse_date(self.date_modified)

    @classmethod
    def get_url(cls, id='me'):
        return '{}/{}/{}/'.format(cls.BASE_URL, cls.RESOURCE, id)

    def get_nodes(self):
        return UserNode.load(self.request_session, self.id)


class Node(BaseResource):
    """Fetch API data relevant to a specific Node"""
    RESOURCE = 'nodes'

    def __init__(self, request_session, data):
        super().__init__(request_session, data)
        self.date_created = iso8601.parse_date(self.date_created)
        self.date_modified = iso8601.parse_date(self.date_modified)

    @classmethod
    def get_url(cls, id):
        return '{}/{}/{}/?embed=parent'.format(cls.BASE_URL, cls.RESOURCE, id)

    def get_storage(self, id='osfstorage'):
        # TODO: At present only osfstorage is fully supported for syncing
        return next(
            storage
            for storage in NodeStorage.load(self.request_session, self.id)
            if storage.provider == id
        )


class UserNode(Node):
    """Fetch API data about nodes owned by a specific user"""
    @classmethod
    def get_url(cls, id):
        return '{}/users/{}/nodes/?filter[registration]=false'.format(cls.BASE_URL, id)


class StorageObject(BaseResource):
    """Represent API data for files or folders under a specific node"""
    @classmethod
    def get_url(cls, id):
        return '{}/files/{}/'.format(cls.BASE_URL, id)

    @classmethod
    def load(cls, request_session, *args):
        resp = request_session.get(cls.get_url(*args), params={'page[size]': 250})
        data = resp.json()

        if isinstance(data['data'], list):
            return [
                (Folder if item['attributes']['kind'] == 'folder' else File)(request_session, item)
                for item in data['data']
            ]
        return cls(request_session, data['data'])

    def __init__(self, request_session, data, parent=None):
        super().__init__(request_session, data)
        self.parent = parent
        if hasattr(self, 'date_modified') and self.date_modified:
            self.date_modified = iso8601.parse_date(self.date_modified)
        if hasattr(self, 'last_touched') and self.last_touched:
            self.last_touched = iso8601.parse_date(self.last_touched)


class Folder(StorageObject):
    """Represent API data for folders under a specific node"""
    is_dir = True

    def get_children(self):
        resp = self.request_session.get(self.raw['relationships']['files']['links']['related']['href'], params={'page[size]': 250})
        data = resp.json()

        if isinstance(data['data'], list):
            l = data['data']
            while data['links'].get('next'):
                resp = self.request_session.get(data['links']['next'], params={'page[size]': 250})
                data = resp.json()
                l.extend(data['data'])
            return [
                (Folder if item['attributes']['kind'] == 'folder' else File)(self.request_session, item, parent=self)
                for item in l
            ]
        return StorageObject(self.request_session, data['data'], parent=self)


class NodeStorage(Folder):
    """Fetch API list of storage options under a node"""
    @classmethod
    def get_url(cls, node_id):
        return '{}/{}/{}/files/'.format(
            cls.BASE_URL,
            Node.RESOURCE,
            node_id
        )


class File(StorageObject):
    """Represent API data for files under a specific node"""
    is_dir = False

    def __repr__(self):
        return '<RemoteFile({}, {}, {}, {}>'.format(self.id, self.name, self.kind, self.parent.id)
