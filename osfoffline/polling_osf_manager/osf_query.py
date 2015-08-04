import asyncio

import aiohttp
import json
from osfoffline.polling_osf_manager.remote_objects \
    import (dict_to_remote_object, RemoteUser, RemoteFolder, RemoteFile, RemoteNode, RemoteObject )
from osfoffline.database_manager.models import File,Node,User
from osfoffline.polling_osf_manager.api_url_builder import wb_file_url,api_file_children, wb_move_url
import osfoffline.alerts as AlertHandler
OK = 200
CREATED = 201
ACCEPTED = 202


class OSFQuery(object):
    def __init__(self, loop, oauth_token):
        self.headers = {
            'Authorization': 'Bearer {}'.format(oauth_token)
        }
        self.request_session = aiohttp.ClientSession(loop=loop, headers=self.headers)

    @asyncio.coroutine
    def _get_all_paginated_members(self, remote_url):
        remote_children = []

        # this is for the case that a new folder is created so does not have the proper links.
        if remote_url is None:
            return remote_children


        resp = yield from self.make_request(remote_url, get_json=True)

        remote_children.extend(resp['data'])
        while resp['links']['next']:

            resp = yield from self.make_request(resp['links']['next'], get_json=True)

            remote_children.extend(resp['data'])

        for child in remote_children:
            assert isinstance(child, dict)

        return remote_children


    @asyncio.coroutine
    def get_top_level_nodes(self, url):
        assert isinstance(url, str)
        all_remote_nodes = yield from self._get_all_paginated_members(url)
        remote_top_level_nodes = []
        for remote in all_remote_nodes:
            if remote['links']['parent']['self'] is None:
                remote_top_level_nodes.append(RemoteNode(remote))
        for node in remote_top_level_nodes:
            assert node.is_top_level
        return remote_top_level_nodes

    @asyncio.coroutine
    def get_child_nodes(self, remote_node):
        assert isinstance(remote_node, RemoteNode)
        nodes = yield from self._get_all_paginated_members(remote_node.child_nodes_url)
        return [dict_to_remote_object(node) for node in nodes]

    @asyncio.coroutine
    def get_child_files(self, remote_node_or_folder):
        assert isinstance(remote_node_or_folder, RemoteNode) or isinstance(remote_node_or_folder, RemoteFolder)
        file_folders = yield from self._get_all_paginated_members(remote_node_or_folder.child_files_url)
        return [dict_to_remote_object(file_folder) for file_folder in file_folders]

    @asyncio.coroutine
    def download_file(self, remote_file):
        assert isinstance(remote_file, RemoteFile)
        file = yield from self.make_request(remote_file.download_url)
        return dict_to_remote_object(file)

    @asyncio.coroutine
    def upload_folder(self, local_folder):
        assert isinstance(local_folder, File)
        assert local_folder.is_folder

        if local_folder.parent:
            path = local_folder.parent.osf_path + local_folder.name
        else:
            path = '/{}'.format(local_folder.name)
        params = {
            'path': path,
            'provider': local_folder.provider,
            'nid': local_folder.node.osf_id
        }
        files_url = wb_file_url()
        resp_json = yield from self.make_request(files_url, method="POST", params=params, get_json=True)
        AlertHandler.info(local_folder.name, AlertHandler.UPLOAD)
        # todo: experimental
        """
        fields that I MUST have are:
            path                                                --already exists in response
            name                                                --use local folder
            provider                                            --user local folder
            item_type                                           --folder
            type                                                --files
            ['links']['related']                                --api_file_children(local_folder.user.osf_id, resp_json['path'], local_folder.provider)
            ['links']['self']                                   --wb_file_url()
            'POST' in remote_dict['links']['self_methods']      --can create this. make POST in there. make this true
            metadata
                modified                                        --CHECK THIS...

        """

        # path exist aleady
        resp_json['name'] = local_folder.name
        resp_json['provider'] = local_folder.provider
        resp_json['item_type'] = 'folder'
        resp_json['type'] = 'files'
        resp_json['links'] = {}
        resp_json['links']['self'] = wb_file_url(path=resp_json['path'], nid=local_folder.node.id, provider=local_folder.provider)
        resp_json['links']['related'] = api_file_children(local_folder.user.osf_id, resp_json['path'], local_folder.provider)
        resp_json['links']['self_methods'] = ['POST']
        resp_json['metadata'] = {}
        resp_json['metadata']['modified'] = 'FAKE TIME. I THINK THIS ALREADY EXISTS IN RESP_JSON'

        return RemoteFolder(resp_json)

    @asyncio.coroutine
    def upload_file(self, local_file):
        """
        THROWS FileNotFoundError !!!!!!
        :param local_file:
        :return:
        """
        assert isinstance(local_file, File)
        assert local_file.is_file
        if local_file.parent:
            path = local_file.parent.osf_path + local_file.name
        else:
            path = '/{}'.format(local_file.name)
        params = {
            'path': path,
            'provider': local_file.provider,
            'nid': local_file.node.osf_id
        }
        files_url = wb_file_url()
        file = open(local_file.path, 'rb')
        resp_json = yield from self.make_request(files_url, method="PUT", params=params, data=file, get_json=True)
        AlertHandler.info(local_file.name, AlertHandler.UPLOAD)
        # todo: experimental
        """
        fields that I MUST have are:
            path                                                --already exists in response
            name                                                --use local folder
            provider                                            --user local folder
            item_type                                           --file
            type                                                --files
            ['links']['self']                                   --wb_file_url(local_folder.user.osf_id, resp_json['path'], local_folder.provider)
            'POST' in remote_dict['links']['self_methods']      --can create this. make POST in there. make this true
            metadata
                modified                                        --CHECK THIS...
                size
                extra
                    hash
                    rented
        """

        # path exist aleady
        resp_json['name'] = local_file.name
        resp_json['provider'] = local_file.provider
        resp_json['item_type'] = 'file'
        resp_json['type'] = 'files'
        resp_json['links'] = {}
        resp_json['links']['self'] = wb_file_url(path=resp_json['path'], nid=local_file.node.id, provider=local_file.provider)
        resp_json['links']['self_methods'] = ['POST', 'GET']
        resp_json['metadata'] = {}
        resp_json['metadata']['modified'] = 'FAKE TIME. I THINK THIS ALREADY EXISTS IN RESP_JSON'
        resp_json['metadata']['size'] = resp_json['size']
        # resp_json['metadata']['extra'] = {}
        # resp_json['metadata']['extra']['hash'] = 'NOT INCLUDED YET
        # resp_json['metadata']['extra']['rented'] = 'NOT INCLUDED YET'
        return RemoteFile(resp_json)


    @asyncio.coroutine
    def rename_remote_file(self, local_file, remote_file):
        assert isinstance(local_file, File)
        assert local_file.is_file
        assert isinstance(remote_file, RemoteFile)

        return (yield from self._rename_remote(local_file, remote_file))


    @asyncio.coroutine
    def rename_remote_folder(self, local_folder, remote_folder):
        assert isinstance(local_folder, File)
        assert local_folder.is_folder
        assert isinstance(remote_folder, RemoteFolder)
        AlertHandler.info(local_folder.name, AlertHandler.MODIFYING)
        return (yield from self._rename_remote(local_folder, remote_folder))


    @asyncio.coroutine
    def _rename_remote(self, local, remote):
        url = wb_move_url()

        data = {
            'rename': local.name,
            'conflict': 'replace',
            'source': {
                'path': local.osf_path,
                'provider': local.provider,
                'nid': local.node.osf_id
            },
            'destination': {
                'path': local.parent.osf_path,
                'provider': local.provider,
                'nid': local.node.osf_id
            }
        }

        resp = yield from self.make_request(url, method="POST", data=json.dumps(data))
        resp.close()

        remote.name = local.name
        return remote

    # @asyncio.coroutine
    # def move_remote_file_folder(self, local_file_folder, remote_file_folder):
    #     """
    #     handles both moving the remote_file_folder and renaming it.
    #     :param local_file_folder:
    #     :param remote_file_folder:
    #     :return:
    #     """
    #     print('rename_remote_file_folder.')
    #     assert isinstance(local_file_folder, File)
    #     assert isinstance(remote_file_folder, dict)
    #     assert remote_file_folder['type'] == 'files'
    #     assert remote_file_folder['path'] == local_file_folder.osf_path
    #     assert local_file_folder.name != remote_file_folder['name'] or local_file_folder.locally_moved
    #
    #     # alerts
    #     alerts.info(local_file_folder.name, alerts.MODIFYING)
    #
    #     new_remote_file_folder = remote_file_folder
    #
    #     # handle renaming for both files and folders
    #
    #     # OSF allows you to manually rename a folder. Use That.
    #     # url = 'https://staging2-files.osf.io/ops/move'
    #
    #     url = wb_move_url()
    #     """
    #     current thinking is that we rename node.top_level_file_folders to node.providers.
    #     We then add a provider boolean to File - node.providers gives you File.provider==True Files
    #     Each File has a provider field. It points to the provider, or None (if the file itself is the provider file)
    #
    #     If we get an event that is trying to move the provider file, we ignore it.
    #     """
    #     data = {
    #         'rename': local_file_folder.name,
    #         'conflict': 'replace',
    #         'source': {
    #             'path': local_file_folder.osf_path,
    #             'provider': local_file_folder.provider,
    #             'nid': local_file_folder.previous_node_osf_id  # fixme: what is the old node id???
    #         },
    #         'destination': {
    #             'path': local_file_folder.parent.osf_path if local_file_folder.parent else '/',  # fixme: parent could be None. in which case we use / for the provider.
    #             'provider': local_file_folder.provider,  # fixme: add validation for moving around osfstorage provider folder. parent=None in this case.
    #             'nid': local_file_folder.node.osf_id
    #         }
    #     }
    #
    #     resp = yield from self.make_request(url, method="POST", data=json.dumps(data))
    #     resp.close()
    #     # get the updated remote folder
    #
    #     # inner_response = requests.get(remote_file_folder['links']['self'], headers=self.headers).json()
    #     # we know exactly what changed, so its faster to just change the remote dictionary rather than making a new api call.
    #
    #     new_remote_file_folder['name'] = data['rename']
    #
    #
    #     return new_remote_file_folder

    @asyncio.coroutine
    def delete_remote_file(self, remote_file):
        assert isinstance(remote_file, RemoteFile)
        yield from self._delete_file_folder(remote_file)
        AlertHandler.info(remote_file.name, AlertHandler.DELETING)

    @asyncio.coroutine
    def delete_remote_folder(self, remote_folder):
        assert isinstance(remote_folder, RemoteFolder)
        yield from self._delete_file_folder(remote_folder)
        AlertHandler.info(remote_folder.name, AlertHandler.DELETING)

    @asyncio.coroutine
    def _delete_file_folder(self, remote_file_folder):
        assert isinstance(remote_file_folder, RemoteFile) or isinstance(remote_file_folder, RemoteFolder)
        url = remote_file_folder.delete_url
        resp = yield from self.make_request(url, method='DELETE')
        resp.close()

    @asyncio.coroutine
    def make_request(self, url, method='GET',params=None, expects=None, get_json=False, timeout=10, data=None):
        try:
            response = yield from asyncio.wait_for(
                self.request_session.request(
                    url=url,
                    method=method.capitalize(),
                    params=params,
                    data=data
                ),
                timeout
            )
        except aiohttp.errors.ClientTimeoutError:
            # internally, if a timeout occurs, aiohttp tries up to 3 times. thus we already technically have retries in.
            AlertHandler.warn("Bad Internet Connection")
            raise
        except aiohttp.errors.BadHttpMessage:

            raise
        except aiohttp.errors.HttpMethodNotAllowed:

            raise
        except aiohttp.errors.ClientConnectionError:
            AlertHandler.warn("Bad Internet Connection")
            raise

        if expects:
            if response.status not in expects:
                raise ConnectionError('failed because of wrong response status. url: {}, expected status: {}, actual status: {}'.format(url, expects, response.status))
        elif 400 <= response.status < 600:
            content = yield from response.read()
            raise ConnectionError('failed {} request {} with expected response code(s) {}. response.content={}'.format(method, url, expects,content ))

        if get_json:
            json_response = yield from response.json()
            return json_response
        return response


    def close(self):
        self.request_session.close()

