"""APIv2 client library for interacting with the OSF API"""

import abc
import asyncio
import iso8601

import aiohttp

from osfoffline import settings


class OSFClient:

    def __init__(self, bearer_token, limit=5):
        self.headers = {
            'Authorization': 'Bearer {}'.format(bearer_token),
        }
        self.throttler = asyncio.Semaphore(limit)
        self.request_session = aiohttp.ClientSession(headers=self.headers)

    @asyncio.coroutine
    def get_node(self, id):
        return (yield from Node.load(self.request_session, id))

    @asyncio.coroutine
    def get_user(self, id='me'):
        return (yield from User.load(self.request_session, id))


class BaseResource(abc.ABC):

    OSF_HOST = settings.API_BASE
    API_PREFIX = 'v2'

    def __init__(self, request_session, data):
        self.request_session = request_session
        self.__dict__.update(data['attributes'])
        self.id = data['id']
        self.type = data['type']
        self.raw = data

    @classmethod
    def get_url(cls, id):
        return '{}/{}/'.format(cls.OSF_HOST, cls.API_PREFIX)

    @classmethod
    @asyncio.coroutine
    def load(cls, request_session, *args):
        resp = yield from request_session.request('GET', cls.get_url(*args), params={'page[size]': 250})
        data = yield from resp.json()
        yield from resp.release()

        if isinstance(data['data'], list):
            l = data['data']
            while data['links'].get('next'):
                resp = yield from request_session.request('GET', data['links']['next'], params={'page[size]': 250})
                data = yield from resp.json()
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
        return '{}/{}/{}/{}/'.format(cls.OSF_HOST, cls.API_PREFIX, cls.RESOURCE, id)

    @asyncio.coroutine
    def get_nodes(self):
        return (yield from UserNode.load(self.request_session, self.id))


class Node(BaseResource):
    """Fetch API data relevant to a specific Node"""
    RESOURCE = 'nodes'

    def __init__(self, request_session, data):
        super().__init__(request_session, data)
        self.date_created = iso8601.parse_date(self.date_created)
        self.date_modified = iso8601.parse_date(self.date_modified)

    @classmethod
    def get_url(cls, id):
        return '{}/{}/{}/{}/'.format(cls.OSF_HOST, cls.API_PREFIX, cls.RESOURCE, id)

    @asyncio.coroutine
    def get_storage(self, id='osfstorage'):
        # TODO: At present only osfstorage is fully supported for syncing
        for storage in (yield from NodeStorage.load(self.request_session, self.id)):
            if storage.provider == id:
                return storage


class UserNode(Node):
    """Fetch API data about nodes owned by a specific user"""
    @classmethod
    def get_url(cls, id):
        return '{}/{}/users/{}/nodes/'.format(cls.OSF_HOST, cls.API_PREFIX, id)


class StorageObject(BaseResource):
    """Represent API data for files or folders under a specific node"""
    @classmethod
    def get_url(cls, id):
        return '{}/{}/files/{}/'.format(cls.OSF_HOST, cls.API_PREFIX, id)

    @classmethod
    @asyncio.coroutine
    def load(cls, request_session, *args):
        resp = yield from request_session.request('GET', cls.get_url(*args), params={'page[size]': 250})
        data = yield from resp.json()
        yield from resp.release()

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

    @asyncio.coroutine
    def get_children(self):
        resp = yield from self.request_session.request('GET', self.raw['relationships']['files']['links']['related']['href'], params={'page[size]': 250})
        data = yield from resp.json()
        yield from resp.release()

        if isinstance(data['data'], list):
            l = data['data']
            while data['links'].get('next'):
                resp = yield from self.request_session.request('GET', data['links']['next'], params={'page[size]': 250})
                data = yield from resp.json()
                yield from resp.release()
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
        # return Node.get_url(node_id) + 'files/' + storage_id + '/'
        return Node.get_url(node_id) + 'files/'


class File(StorageObject):
    """Represent API data for files under a specific node"""
    is_dir = False

    @asyncio.coroutine
    def download(self):
        """Download file content from the storage provider"""
        # TODO: Can this be done without the coroutine? (while still using aiohttp) Make blocking maybe?
        url = self.raw['links']['download']
        resp = yield from self.request_session.request('GET', url)
        while True:
            chunk = yield from resp.content.read(1024 * 64)
            if not chunk:
                break
            yield chunk
        yield from resp.release()

    def __repr__(self):
        return "<File ({}), kind={}, name={}, parent_id={}>".format(self.id, self.kind, self.name, self.parent_id)
