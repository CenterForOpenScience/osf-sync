__author__ = 'himanshu'
import json
import os
import asyncio
import shutil
import iso8601
import pytz
import aiohttp
import concurrent
from osfoffline.models import User, Node, File, Base
import osfoffline.alerts as alerts
import osfoffline.db as db
from osfoffline.api_url_builder import api_user_url, wb_file_revisions, wb_file_url, api_user_nodes,wb_move_url

OK = 200
CREATED = 201
ACCEPTED = 202
RECHECK_TIME = 5  # in seconds


class Poll(object):
    def __init__(self, user_osf_id, loop):
        super().__init__()
        self._keep_running = True
        self.user_osf_id = user_osf_id
        self.session = db.get_session()
        self.user = self.session.query(User).filter(
            User.osf_id == user_osf_id).one()  # todo: does passing in user directly break things?

        # todo: make headers be from a remote desktop client
        # todo: make a method make_request that handles putting in header. puts in Auth. streams. async.

        self.headers = {
            'Cookie': 'osf_staging2=55a3d4f3404f7756a1d84d32.iHwM3kRshA2P8TVJq2i0J7iNxgY;',  # for v1 api
            'Authorization': 'Bearer {}'.format(self.user.oauth_token)  # for v2 api
        }
        self._loop = loop

        self.request_session = aiohttp.ClientSession(loop=self._loop, headers=self.headers)

    def stop(self):
        self._keep_running = False


    def start(self):
        # annoying and weird way to get the remote user from the coroutine
        future = asyncio.Future()
        asyncio.async(self.get_remote_user(future), loop=self._loop)
        self._loop.run_until_complete(future)
        remote_user = future.result()

        self._loop.call_soon(
            asyncio.async,
            self.check_osf(remote_user)
        )

    # Only once you have a remote user do we want to check the osf.
    # thus this coroutine repeatedly tries to get the remote user.
    @asyncio.coroutine
    def get_remote_user(self, future):
        print("checking projects of user with id {}".format(self.user_osf_id))
        url = api_user_url(self.user_osf_id)
        while True:
            try:
                resp = yield from self.make_request(url, get_json=True)
                future.set_result(resp['data'])
                break
            except concurrent.futures._base.TimeoutError:
                print('failed to get remote_user. trying again.')
            except aiohttp.errors.ClientTimeoutError:
                print('failed to get remote_user. trying again.')

    def get_id(self, item):
        """
        This function determines the rules to get the id for a local or remote representation of nodes/files.
        The ways to get the id differ based on the input item type:
            local node -> osf_id ( this is node id (nid) on the OSF )
            local file -> osf_path (this is osf_path)hash(node.osf_id, provider name, osf path)
                ( note, osf path is the 'path' variable provided by waterbutler. It is represented as '/<unique waterbutler identifier>'
            remote node -> id (this is the node if (nid) on the OSF )
            remote file -> path ( this is the path ( '/<unique waterbutler identifier>' ) on the OSF )

        :param item: local (sql alchemy Base object) or remote (dict) representation of a node or file
        :return: the input items id
        """
        # if node/file is remote
        if isinstance(item, dict):
            if item['type'] == 'nodes':
                return item['id']
            elif item['type'] == 'files':
                return item['path']
            else:
                raise ValueError(item['type'] + 'is not handled')
        elif isinstance(item, Base):
            if item.osf_id:
                return item.osf_id
            else:
                assert item.locally_created
                return "{}".format(item.id)
        else:
            raise ValueError('What the fudge did you pass in?')

    def make_local_remote_tuple_list(self, local_list, remote_list):
        """
        Create a list of tuples where the local and remote representation of the node/file are grouped together.
        This allows us to determine differences between the local and remote versions and perform appropriate functions
        on them. This tuple list is the backbone behind the polling scheme in this file.

        Notably, the connection between the local and remote is made in differing manners depending on whether
        the input is a node or file. Each input is given an id, as determined by the get function above.
        These id's are then matched to create a tuple. If an id has no match, it is matched with None.


        :param local_list: list of local node or file sql alchemy objects
        :param remote_list: list of dicts from the osf v2 api representing nodes or files
        :return: list of tuples with the left being the local version of node or file and
                 the right being the remote version. aka. [ (local, remote),... ]
        """
        assert None not in local_list
        assert None not in remote_list

        combined_list = local_list + remote_list
        sorted_combined_list = sorted(combined_list, key=self.get_id)

        local_remote_tuple_list = []
        i = 0
        while i < len(sorted_combined_list):


            both_exist = i + 1 < len(sorted_combined_list) and \
                self.get_id(sorted_combined_list[i]) == \
                self.get_id(sorted_combined_list[i + 1])
            if both_exist:

                # (local, remote)
                if isinstance(sorted_combined_list[i], dict):  # remote
                    new_tuple = (sorted_combined_list[i + 1], sorted_combined_list[i])
                elif isinstance(sorted_combined_list[i], Base):  # local
                    new_tuple = (sorted_combined_list[i], sorted_combined_list[i + 1])
                else:
                    raise TypeError('what the fudge did you pass in')

                # add an extra 1 because both values should be added to tuple list
                i += 1
            elif isinstance(sorted_combined_list[i], dict):

                new_tuple = (None, sorted_combined_list[i])

            else:

                new_tuple = (sorted_combined_list[i], None)

            local_remote_tuple_list.append(new_tuple)
            i += 1

        for local, remote in local_remote_tuple_list:

            assert isinstance(local, Base) or local is None
            assert isinstance(remote, dict) or remote is None
            if isinstance(local, Base) and isinstance(remote, dict):
                assert local.osf_id == self.get_id(remote)

        return local_remote_tuple_list

    # Check

    @asyncio.coroutine
    def check_osf(self, remote_user):
        print('check_osf')
        assert isinstance(remote_user, dict)
        assert remote_user['type'] == 'users'

        remote_user_id = remote_user['id']

        # all_remote_nodes_url = 'https://staging2.osf.io:443/api/v2/users/{}/nodes/'.format(remote_user_id)
        all_remote_nodes_url = api_user_nodes(remote_user_id)
        while self._keep_running:
            # get remote top level nodes
            all_remote_nodes = yield from self.get_all_paginated_members(all_remote_nodes_url)
            remote_top_level_nodes = []
            # print(all_remote_nodes)
            for remote in all_remote_nodes:
                if remote['links']['parent']['self'] is None:
                    print(remote)
                    remote_top_level_nodes.append(remote)


            # get local top level nodes
            local_top_level_nodes = self.user.top_level_nodes

            local_remote_top_level_nodes = self.make_local_remote_tuple_list(local_top_level_nodes, remote_top_level_nodes)


            for local, remote in local_remote_top_level_nodes:


                # optimization: could check date modified of top level
                # and if not modified then don't worry about children
                yield from self.check_node(local, remote, local_parent_node=None)

            print('---------SHOULD HAVE ALL OSF FILES---------')

            yield from asyncio.sleep(RECHECK_TIME)
            # todo: figure out how we can prematuraly stop the sleep when user ends the application while sleeping

    @asyncio.coroutine
    def check_node(self, local_node, remote_node, local_parent_node):
        """
        Responsible for checking whether local node values are same as remote node.
        Values to be checked include: files and folders, name, metadata, child nodes

        VARIOUS STATES (update as neccessary):
        (None, None) -> Error                       --
        (None, remote) -> create local              --
        (local.create, None) -> create remote       --
        (local.create, remote) -> ERROR             --
        (local.delete, None) -> ERROR               --
        (local.delete, remote) - > delete remote    --
        (local, None) -> delete local
        (local, remote) -> check modifications

        """
        print('checking node')
        assert (local_node is not None) or (remote_node is not None)  # both shouldnt be none.
        assert (local_parent_node is None) or isinstance(local_parent_node, Node)

        if local_node is None:
            local_node = yield from self.create_local_node(remote_node, local_parent_node)
        elif local_node is not None and remote_node is None:
            yield from self.delete_local_node(local_node)
            return
        elif local_node is not None and remote_node is not None:
            # todo: handle other updates to  node

            if local_node.title != remote_node['title']:
                yield from self.modify_local_node(local_node, remote_node)

        # handle file_folders for node
        yield from self.check_file_folder(local_node, remote_node)

        # recursively handle node's children
        remote_children = yield from self.get_all_paginated_members(remote_node['links']['children']['related'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.child_nodes, remote_children)
        for local, remote in local_remote_nodes:
            yield from self.check_node(local, remote, local_parent_node=local_node)

    # todo: determine if we just want osfstorage or also other things
    @asyncio.coroutine
    def check_file_folder(self, local_node, remote_node):
        print('checking file_folder')

        remote_node_files = yield from self.get_all_paginated_members(remote_node['links']['files']['related'])
        local_remote_files = self.make_local_remote_tuple_list(local_node.top_level_file_folders, remote_node_files)

        for local, remote in local_remote_files:
            yield from self._check_file_folder(local, remote, local_parent_file_folder=None,
                                    local_node=local_node)
    @asyncio.coroutine
    def _check_file_folder(self,
                           local_file_folder,
                           remote_file_folder,
                           local_parent_file_folder,
                           local_node):
        """
        VARIOUS STATES (update as neccessary):
        (None, None) -> Error                       --
        (None, remote) -> create local              --
        (local.create, None) -> create remote       --
        (local.create, remote) -> ERROR             --
        (local.delete, None) -> ERROR               --
        (local.delete, remote) - > delete remote    --
        (local, None) -> delete local               --
        (local, remote) -> check modifications      --

        """
        assert local_file_folder or remote_file_folder  # both shouldnt be None.

        print('checking file_folder internal')
        if local_file_folder is None:
            local_file_folder = yield from self.create_local_file_folder(remote_file_folder, local_parent_file_folder, local_node)
        elif local_file_folder.locally_created and remote_file_folder is None:
            # todo: this is broken for now. Need to figure out a diff way to do this.
            remote_file_folder = yield from self.create_remote_file_folder(local_file_folder, local_node)
            return
        elif local_file_folder.locally_created and remote_file_folder is not None:
            raise ValueError('newly created local file_folder was already on server for some reason. why? fixit!')
        elif local_file_folder.locally_deleted and remote_file_folder is None:
            raise ValueError('local file_folder was never on server for some reason. why? fixit!')
        elif local_file_folder.locally_deleted and remote_file_folder is not None:
            yield from self.delete_remote_file_folder(local_file_folder, remote_file_folder)
            return
        elif local_file_folder is not None and remote_file_folder is None:
            yield from self.delete_local_file_folder(local_file_folder)
            return
        elif local_file_folder is not None and remote_file_folder is not None:
            # todo: this is broken for now as well. Need additional functionalities on server for this.
            # todo: diff way to do this is also good.
            possibly_new_remote_file_folder = yield from self.modify_file_folder_logic(local_file_folder, remote_file_folder)
            if possibly_new_remote_file_folder:
                remote_file_folder = possibly_new_remote_file_folder
        else:
            raise ValueError('in some weird state. figure it out.')

        assert local_file_folder is not None
        assert remote_file_folder is not None

        # recursively handle folder's children
        if local_file_folder.type == File.FOLDER:
            try:
                remote_children = yield from self.get_all_paginated_members(remote_file_folder['links']['related'])
                local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)
                for local, remote in local_remote_file_folders:
                    yield from self._check_file_folder(local,
                                            remote,
                                            local_parent_file_folder=local_file_folder,
                                            local_node=local_node)
            except ConnectionError:
                pass
                # if we are unable to get children, then we do not try to get and manipulate children

    @asyncio.coroutine
    def get_all_paginated_members(self, remote_url):
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

    # Create
    @asyncio.coroutine
    def create_local_node(self, remote_node, local_parent_node):
        print('create_local_node')
        assert isinstance(remote_node, dict)
        assert remote_node['type'] == 'nodes'
        assert isinstance(local_parent_node, Node) or local_parent_node is None

        # create local node in db
        category = Node.PROJECT if remote_node['category'] == 'project' else Node.COMPONENT
        new_node = Node(
            title=remote_node['title'],
            category=category,
            osf_id=remote_node['id'],
            user=self.user,
            parent=local_parent_node
        )
        db.save(self.session, new_node)

        # alert
        alerts.info(new_node.title, alerts.DOWNLOAD)

        # create local node folder on filesystem
        if not os.path.exists(new_node.path):
            os.makedirs(new_node.path)

        assert local_parent_node is None or (new_node in local_parent_node.child_nodes)
        return new_node


    @asyncio.coroutine
    def create_local_file_folder(self, remote_file_folder, local_parent_folder, local_node):
        print('creating local file folder')
        assert remote_file_folder is not None
        assert remote_file_folder['type'] == 'files'
        assert isinstance(local_parent_folder, File) or local_parent_folder is None
        assert local_parent_folder is None or (local_parent_folder.type == File.FOLDER)
        assert isinstance(local_node, Node)

        # create local file folder in db
        type = File.FILE if remote_file_folder['item_type'] == 'file' else File.FOLDER
        new_file_folder = File(
            name=remote_file_folder['name'],
            type=type,
            osf_id=self.get_id(remote_file_folder),
            provider=remote_file_folder['provider'],
            osf_path=remote_file_folder['path'],
            user=self.user,
            parent=local_parent_folder,
            node=local_node
        )
        db.save(self.session, new_file_folder)
        if 'stream' in new_file_folder.name:
            print('STREAM FILE WAS CREATED LOCALLY.')
        # alert
        alerts.info(new_file_folder.name, alerts.DOWNLOAD)

        # create local file/folder on actual system
        if not os.path.exists(new_file_folder.path):
            if type == File.FILE:
                resp = yield from self.make_request(remote_file_folder['links']['self'])
                with open(new_file_folder.path, 'wb') as fd:
                    while True:
                        chunk = yield from resp.content.read(2048)
                        if not chunk:
                            break
                        fd.write(chunk)
                    resp.close()
            elif type == File.FOLDER:
                os.makedirs(new_file_folder.path)
            else:
                raise ValueError('file type is unknown')
        return new_file_folder


    @asyncio.coroutine
    def create_remote_file_folder(self, local_file_folder, local_node):
        print('create_remote_file_folder')
        assert local_file_folder is not None
        assert isinstance(local_file_folder, File)
        assert local_node is not None
        assert isinstance(local_node, Node)
        assert local_file_folder.locally_created

        # alert
        alerts.info(local_file_folder.name, alerts.DOWNLOAD)

        if local_file_folder.parent:
            path = local_file_folder.parent.osf_path + local_file_folder.name
        else:
            path = '/{}'.format(local_file_folder.name)
        params = {
            'path': path,
            'provider': local_file_folder.provider,
            'nid': local_node.osf_id
        }

        # files_url = 'https://staging2-files.osf.io/file'  # todo: make this global
        files_url = wb_file_url()
        resp = None
        if local_file_folder.type == File.FOLDER:
            resp = yield from self.make_request(files_url,method="POST", params=params, get_json=True)
        elif local_file_folder.type == File.FILE:

            try:
                file = open(local_file_folder.path, 'rb')
                resp = yield from self.make_request(files_url, method="PUT", params=params, data=file, get_json=True)
            except FileNotFoundError:
                print('file not created on remote server because does not exist locally. inside create_remote_file_folder')
                return
            except IsADirectoryError:
                local_file_folder.type = File.FOLDER
                db.save(self.session, local_file_folder)
                return

        remote_file_folder = resp

        # add additional fields to make it like a regular remote_file_folder
        remote_file_folder['type'] = 'files'
        remote_file_folder['item_type'] = remote_file_folder['kind']
        remote_file_folder['links'] = {}
        remote_file_folder['links']['related'] = None

        local_file_folder.osf_id = self.get_id(remote_file_folder)
        local_file_folder.osf_path = remote_file_folder['path']
        local_file_folder.locally_created = False
        db.save(self.session,local_file_folder)

        return remote_file_folder

    # Modify
    @asyncio.coroutine
    def modify_local_node(self, local_node, remote_node):
        print('modify_local_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, dict)
        assert remote_node['type'] == 'nodes'
        assert remote_node['id'] == local_node.osf_id

        old_path = local_node.path
        local_node.title = remote_node['title']
        # todo: handle other fields such as category, hash, ...
        db.save(self.session,local_node)

        # alert
        alerts.info(local_node.title, alerts.MODIFYING)

        # modify local node on filesystem
        try:
            os.renames(old_path, local_node.path)
        except FileNotFoundError:
            print('renaming of file failed because file not there. inside modify_local_node')

    @asyncio.coroutine
    def modify_file_folder_logic(self, local_file_folder, remote_file_folder):
        assert isinstance(local_file_folder,File)
        assert isinstance(remote_file_folder,dict)

        updated_remote_file_folder = None
        # this handles both files and folders being renamed
        if local_file_folder.name != remote_file_folder['name']:
            if (yield from self.local_is_newer(local_file_folder, remote_file_folder)):
                updated_remote_file_folder = yield from self.rename_remote_file_folder(local_file_folder, remote_file_folder)
            else:
                yield from self.rename_local_file_folder(local_file_folder,  remote_file_folder)

        # if file size is different, then only do you  bother checking whether to upload or to download
        if local_file_folder.type == File.FILE and local_file_folder.size != remote_file_folder['metadata']['size']:
            if (yield from self.local_is_newer(local_file_folder, remote_file_folder)):
                updated_remote_file_folder = yield from self.update_remote_file(local_file_folder, remote_file_folder)
            elif (yield from self.remote_is_newer(local_file_folder, remote_file_folder)):
                yield from self.update_local_file(local_file_folder, remote_file_folder)

        # want to have the remote file folder continue to be the most recent version.
        return updated_remote_file_folder

    @asyncio.coroutine
    def rename_local_file_folder(self, local_file_folder, remote_file_folder):
        print('modify_local_file_folder')
        assert isinstance(local_file_folder, File)
        assert isinstance(remote_file_folder, dict)
        assert remote_file_folder['type'] == 'files'
        assert remote_file_folder['path'] == local_file_folder.osf_path


        # alerts
        alerts.info(local_file_folder.name, alerts.MODIFYING)

        #handle renaming local file and local folder
        old_path = local_file_folder.path
        # update model
        local_file_folder.name = remote_file_folder['name']
        db.save(self.session, local_file_folder)


        # update local file system
        try:
            os.renames(old_path, local_file_folder.path)
        except FileNotFoundError:
            print('folder not modified because doesnt exist. inside modify_local_file_folder (1)')

    @asyncio.coroutine
    def update_local_file(self, local_file, remote_file):
        assert isinstance(local_file, File)
        assert isinstance(remote_file, dict)
        assert remote_file['type'] == 'files'
        assert remote_file['path'] == local_file.osf_path
        assert remote_file['item_type'] == 'file'


        # todo: need the db file to be updated to show that its timestamp is in fact updated.
        # todo: can read this: http://docs.sqlalchemy.org/en/improve_toc/orm/events.html

        # update model
        # self.save(local_file_folder) # todo: this does NOT actually update the local_file_folder timestamp
        # update local file system
        try:
            resp = yield from self.make_request(remote_file['links']['self'])
            # todo: which is better? 1024 or 2048? Apparently, not much difference.

            with open(local_file.path, 'wb') as fd:
                while True:
                    console_log('wrote 2048 chunk to file with path ',local_file.path)
                    chunk = yield from resp.content.read(2048)
                    if not chunk:
                        break
                    fd.write(chunk)
                resp.close()
        # file was deleted locally.
        except FileNotFoundError:
            print('file not updated locally because it doesnt exist. inside modify_local_file_folder (2)')


    @asyncio.coroutine
    def update_remote_file(self, local_file, remote_file):
        print('update_remote_file')
        assert isinstance(local_file, File)
        assert isinstance(remote_file, dict)
        assert remote_file['type'] == 'files'
        assert remote_file['path'] == local_file.osf_path
        assert remote_file['item_type'] == 'file'

        alerts.info(local_file.name, alerts.MODIFYING)

        local_node = local_file.node

        params = {
            'path': local_file.osf_path,
            'provider': local_file.provider,
            'nid': local_node.osf_id
        }
        # files_url = 'https://staging2-files.osf.io/file'  # todo: make this global

        files_url = wb_file_url()

        try:
                console_log('this is where the error is','making some dumb temp file and breaking everything.')
                file = open(local_file.path, 'rb')

                remote_file_folder = yield from self.make_request(
                    files_url,
                    method='PUT',
                    params=params,
                    data=file,
                    get_json=True
                )

        except FileNotFoundError:
            print('file not created on remote server because does not exist locally. inside create_remote_file_folder')
            return remote_file



        # add additional fields to make it like a regular remote_file_folder
        remote_file_folder['type'] = 'files'
        remote_file_folder['item_type'] = remote_file_folder['kind']
        remote_file_folder['links'] = {}
        remote_file_folder['links']['related'] = None

        return remote_file_folder

    @asyncio.coroutine
    def rename_remote_file_folder(self, local_file_folder, remote_file_folder):
        print('rename_remote_file_folder.')
        assert isinstance(local_file_folder, File)
        assert isinstance(remote_file_folder, dict)
        assert remote_file_folder['type'] == 'files'
        assert remote_file_folder['path'] == local_file_folder.osf_path
        assert local_file_folder.name != remote_file_folder['name']

        # alerts
        alerts.info(local_file_folder.name, alerts.MODIFYING)

        new_remote_file_folder = remote_file_folder

        # handle renaming for both files and folders

        # OSF allows you to manually rename a folder. Use That.
        # url = 'https://staging2-files.osf.io/ops/move'
        url = wb_move_url()
        data = {
            'rename': local_file_folder.name,
            'conflict': 'replace',
            'source': {
                'path': local_file_folder.osf_path,
                'provider': local_file_folder.provider,
                'nid': local_file_folder.node.osf_id
            },
            'destination': {
                'path': local_file_folder.parent.osf_path,
                'provider': local_file_folder.provider,
                'nid': local_file_folder.node.osf_id
            }
        }

        resp = yield from self.make_request(url, method="POST", data=json.dumps(data))
        resp.close()
        # get the updated remote folder

        # inner_response = requests.get(remote_file_folder['links']['self'], headers=self.headers).json()
        # we know exactly what changed, so its faster to just change the remote dictionary rather than making a new api call.

        new_remote_file_folder['name'] = data['rename']


        return new_remote_file_folder

    # Delete
    @asyncio.coroutine
    def delete_local_node(self, local_node):
        print('delete_local_node')
        assert isinstance(local_node, Node)


        path = local_node.path

        # alerts
        alerts.info(local_node.title, alerts.DELETING)

        # delete model
        self.session.delete(local_node)
        db.save(self.session)

        # delete from local
        # todo: avoids_symlink_attacks: https://docs.python.org/3.4/library/shutil.html#shutil.rmtree.avoids_symlink_attacks
        # todo: make better error handling.
        shutil.rmtree(path, onerror=lambda a, b, c: print('local node not deleted because not exists.'))


    @asyncio.coroutine
    def delete_local_file_folder(self, local_file_folder):
        print('delete_local_file_folder')
        assert isinstance(local_file_folder, File)

        path = local_file_folder.path
        file_folder_type = local_file_folder.type
        # delete model
        self.session.delete(local_file_folder)
        db.save(self.session)

        # alerts
        alerts.info(local_file_folder.name, alerts.DELETING)

        # delete from local
        if file_folder_type == File.FOLDER:
            # todo: avoids_symlink_attacks: https://docs.python.org/3.4/library/shutil.html#shutil.rmtree.avoids_symlink_attacks
            # todo: make better error handling.
            # I think my preferred solution for this is to just NOT follow any symlinks
            shutil.rmtree(path,
                          onerror=lambda a, b, c: print('delete local folder failed because folder already deleted. inside delete_local_file_folder(1)'))
        else:
            try:
                os.remove(path)
            except FileNotFoundError:
                print('file not deleted because does not exist on local filesystem. inside delete_local_file_folder (2)')

    @asyncio.coroutine
    def delete_remote_file_folder(self, local_file_folder, remote_file_folder):
        print('delete_remote_file_folder')
        assert local_file_folder is not None
        assert remote_file_folder is not None
        assert local_file_folder.osf_id == self.get_id(remote_file_folder)
        assert local_file_folder.locally_deleted

        # alerts
        alerts.info(local_file_folder.name, alerts.DELETING)

        url = remote_file_folder['links']['self']

        resp = yield from self.make_request(url, method="DELETE")
        resp.close()

        local_file_folder.deleted = False
        self.session.delete(local_file_folder)
        db.save(self.session)



    # todo: determine proper logic for when to update local/remote. (specifically for files based on datetime for now.)
    @asyncio.coroutine
    def _get_local_remote_times(self, local, remote):
        assert local
        assert remote
        assert isinstance(local, Base)
        assert isinstance(remote, dict)

        local_time = local.date_modified.replace(tzinfo=pytz.utc)
        remote_time_string = None

        # nodes and folders
        if 'date_modified' in remote and remote['date_modified']:
            remote_time_string = remote['date_modified']
        # file
        elif 'metadata' in remote and 'modified' in remote['metadata'] and remote['metadata']['modified']:
            remote_time_string = remote['metadata']['modified']
        # times from online are None
        elif remote['type'] == 'files' and remote['item_type'] == 'file':
            # url = 'https://staging2-files.osf.io/revisions'
            url = wb_file_revisions()
            params = {
                'path':local.osf_path,
                'provider':local.provider,
                'nid':local.node.osf_id,
            }
            resp = yield from self.make_request(url, params=params, get_json=True)
            remote_time_string = resp['data'][0]['modified']
            for revision in resp['data']:
                assert self.remote_to_local_datetime(remote_time_string) >= self.remote_to_local_datetime(revision['modified'])

        # if times from online for node are None, you are screwed.

        try:
            remote_time = self.remote_to_local_datetime(remote_time_string)
        except iso8601.ParseError:
            remote_time = None

        return local_time, remote_time

    # NOTE: waterbutler does not give a 'modified' time to something that has been created.
    # THUS, if we are modifying something and remote is None, the modification MUST be coming from local.

    @asyncio.coroutine
    def local_is_newer(self, local, remote):
        assert local
        assert remote
        local_time, remote_time = yield from self._get_local_remote_times(local, remote)

        # fixme: for now, if remote is None, then most recent is whichever one is bigger.
        if remote_time is None:

            if remote['type'] == 'files' and remote['item_type'] == 'file':
                return local.size > remote['metadata']['size']
            else:
                return True

        return local_time > remote_time

    @asyncio.coroutine
    def remote_is_newer(self, local, remote):
        assert local
        assert remote
        local_time, remote_time = yield from self._get_local_remote_times(local, remote)
        # fixme: what should remote_time is None do???
        if remote_time is None:
            if remote['type'] == 'files' and remote['item_type'] == 'file':
                return local.size < remote['metadata']['size']
            else:
                return False

        return local_time < remote_time

    def remote_to_local_datetime(self, remote_utc_time_string):
        """convert osf utc time string to a proper datetime (with utc timezone).
            throws iso8601.ParseError. Handle as needed.
        """
        return iso8601.parse_date(remote_utc_time_string)

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
            # try again. if fail again, then raise error.
            response = yield from self.request_session.request(
                url=url,
                method=method,
            )
        except aiohttp.errors.BadHttpMessage:
            print('failed request for url {}'.format(url))
            raise
        except aiohttp.errors.HttpMethodNotAllowed:
            print('method not allowed {}'.format(method))
            raise
        except aiohttp.errors.ClientConnectionError:
            print("These aren't the domains we're looking for.")
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

def console_log(variable_name, variable_value):
    print("DEBUG: {}: {}".format(variable_name, variable_value))