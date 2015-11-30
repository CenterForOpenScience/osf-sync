import abc
import asyncio
import iso8601

import aiohttp


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


class BaseResource(abc.ABC):

    # OSF_HOST = 'staging-api.osf.io'
    OSF_HOST = 'api.osf.io'
    API_PREFIX = 'v2'

    def __init__(self, request_session, data):
        self.request_session = request_session
        self.__dict__.update(data['attributes'])
        self.id = data['id']
        self.type = data['type']
        self.raw = data

    @classmethod
    def get_url(cls, id):
        return 'https://{}/{}/'.format(cls.OSF_HOST, cls.API_PREFIX)

    @classmethod
    @asyncio.coroutine
    def load(cls, request_session, *args):
        resp = yield from request_session.request('GET', cls.get_url(*args))
        data = yield from resp.json()

        if isinstance(data['data'], list):
            return [cls(request_session, item) for item in data['data']]
        return cls(request_session, data['data'])


class Node(BaseResource):

    RESOURCE = 'nodes'

    def __init__(self, request_session, data):
        super().__init__(request_session, data)
        self.date_created = iso8601.parse_date(self.date_created)
        self.date_modified = iso8601.parse_date(self.date_modified)

    @classmethod
    def get_url(cls, id):
        return 'https://{}/{}/{}/{}/'.format(cls.OSF_HOST, cls.API_PREFIX, cls.RESOURCE, id)

    @asyncio.coroutine
    def get_storage(self, id):
        return (yield from NodeStorage.load(self.request_session, self.id, id))


class StorageObject(BaseResource):

    @classmethod
    def get_url(cls, id):
        return 'https://{}/{}/files/{}/'.format(cls.OSF_HOST, cls.API_PREFIX, id)

    @classmethod
    @asyncio.coroutine
    def load(cls, request_session, *args):
        resp = yield from request_session.request('GET', cls.get_url(*args))
        data = yield from resp.json()

        if isinstance(data['data'], list):
            return [
                (Folder if item['attributes']['kind'] == 'folder' else File)(request_session, item)
                for item in data['data']
            ]
        return cls(request_session, data['data'])

    def __init__(self, request_session, data):
        super().__init__(request_session, data)
        if self.date_modified:
            self.date_modified = iso8601.parse_date(self.date_modified)
        if self.last_touched:
            self.last_touched = iso8601.parse_date(self.last_touched)


class Folder(StorageObject):
    is_dir = True

    @asyncio.coroutine
    def get_children(self):
        resp = yield from self.request_session.request('GET', self.raw['relationships']['files']['links']['related']['href'])
        data = yield from resp.json()

        if isinstance(data['data'], list):
            return [
                (Folder if item['attributes']['kind'] == 'folder' else File)(self.request_session, item)
                for item in data['data']
            ]
        return StorageObject(self.request_session, data['data'])



class NodeStorage(Folder):

    @classmethod
    def get_url(cls, node_id, storage_id):
        return Node.get_url(node_id) + 'files/' + storage_id + '/'



class File(StorageObject):
    is_dir = False
