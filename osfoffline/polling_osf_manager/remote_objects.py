"""
Things to validate:
    1) actually turn modified string to timestamp
        handle when this doesnt exist and whatever else this needs to do.
    2) check type is correct
    3) check file versus folder
    4) check if each remote thing exist. IF NOT, then raise error (done automatically so i guess thats good)

"""
import asyncio
import iso8601
from osfoffline.polling_osf_manager.api_url_builder import wb_file_revisions


class RemoteObject(object):
    def __init__(self, remote_dict):
        assert isinstance(remote_dict, dict)
        assert 'type' in remote_dict
        self.id = None
        self.name = None

    def validate(self):
        assert self.id
        assert self.name


class RemoteUser(RemoteObject):
    def __init__(self, remote_dict):
        super().__init__(remote_dict)
        assert remote_dict['type'] == 'users'
        self.id = remote_dict['id']
        self.name = remote_dict['fullname']
        self.child_nodes_url = remote_dict['links']['nodes']['relation']

        self.validate()


class RemoteNode(RemoteObject):
    def __init__(self, remote_dict):
        super().__init__(remote_dict)
        assert remote_dict['type'] == 'nodes'
        self.id = remote_dict['id']
        self.name = remote_dict['title']
        self.category = remote_dict['category'] if remote_dict['category'] else 'other'
        self.child_files_url = remote_dict['links']['files']['related']
        self.is_top_level = remote_dict['links']['parent']['self'] is None
        self.child_nodes_url = remote_dict['links']['children']['related']

        self._date_modified = remote_dict['date_modified']

        self.validate()

    @property
    def last_modified(self):
        return remote_to_local_datetime(self._date_modified)

    def validate(self):
        super().validate()
        assert self.category
        assert self.child_files_url
        assert self.is_top_level is not None
        assert self.child_nodes_url
        assert self.last_modified


class RemoteFileFolder(RemoteObject):
    def __init__(self, remote_dict):
        super().__init__(remote_dict)
        assert remote_dict['type'] == 'files'
        self.id = remote_dict['path']
        self.name = remote_dict['name']
        self.provider = remote_dict['provider']
        self._metadata = remote_dict['metadata']



    def validate(self):
        super().validate()
        assert self.provider
        assert self._metadata is not None


    @asyncio.coroutine
    def last_modified(self, node_id, osf_query):
        import pdb;pdb.set_trace()
        remote_time_string = None
        if 'modified' in self._metadata and self._metadata['modified']:
            remote_time_string = self._metadata['modified']
        # times from online are None
        elif node_id and osf_query:
                # todo: determine what I should query here.
                url = wb_file_revisions()
                params = {
                    'path': self.id,
                    'provider': self.provider,
                    'nid': node_id,
                }
                resp = yield from osf_query.make_request(url, params=params, get_json=True)
                remote_time_string = resp['data'][0]['modified']
                for revision in resp['data']:
                    assert remote_to_local_datetime(remote_time_string) \
                        >=\
                        remote_to_local_datetime(revision['modified'])
        return remote_to_local_datetime(remote_time_string)


class RemoteFolder(RemoteFileFolder):
    def __init__(self, remote_dict):

        super().__init__(remote_dict)
        assert remote_dict['item_type'] == 'folder'

        self.child_files_url = remote_dict['links']['related']
        self.delete_url = remote_dict['links']['self']
        self.has_write_privileges = 'POST' in remote_dict['links']['self_methods']

        self.validate()

    def validate(self):
        super().validate()
        assert self.child_files_url
        assert self.delete_url
        assert self.has_write_privileges is not None


class RemoteFile(RemoteFileFolder):
    def __init__(self, remote_dict):
        super().__init__(remote_dict)
        assert remote_dict['item_type'] == 'file'

        # todo: if something is rented, do i even have access to view it??????
        assert 'GET' in remote_dict['links']['self_methods']

        self.download_url = remote_dict['links']['self']
        self.delete_url = self.download_url
        # self.hash = remote_dict['metadata']['extra']['hash']
        # self.rented = remote_dict['metadata']['extra']['rented']
        self.size = remote_dict['metadata']['size']

        self._write_privileges = 'POST' in remote_dict['links']['self_methods']

        self.validate()

    @property
    def has_write_privileges(self):
        # if self.rented:
        #     return False
        return self._write_privileges

    def validate(self):
        super().validate()
        assert self.download_url
        assert self.delete_url
        assert self.size >= 0
        assert self.has_write_privileges is not None


def dict_to_remote_object(remote_dict):
    assert isinstance(remote_dict, dict)
    if remote_dict['type'] == 'files':
        if remote_dict['item_type'] == 'file':
            return RemoteFile(remote_dict)
        else:
            return RemoteFolder(remote_dict)
    elif remote_dict['type'] == 'nodes':
        return RemoteNode(remote_dict)
    elif remote_dict['type'] == 'users':
        return RemoteUser(remote_dict)
    else:
        raise TypeError('unable to convert dict {} to RemoteObject'.format(remote_dict))


def remote_to_local_datetime(remote_utc_time_string):
        """convert osf utc time string to a proper datetime (with utc timezone).
            throws iso8601.ParseError. Handle as needed.
        """
        return iso8601.parse_date(remote_utc_time_string)