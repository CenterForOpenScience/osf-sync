__author__ = 'himanshu'
import json
import os
import asyncio
import shutil
import iso8601
import pytz
import aiohttp

from models import User, Node, File, get_session, Base
import alerts

OK = 200
CREATED = 201
ACCEPTED = 202
RECHECK_TIME = 5  # in seconds


class Poll(object):
    def __init__(self, user_osf_id, loop):
        super().__init__()
        self._keep_running = True
        self.user_osf_id = user_osf_id
        self.session = get_session()
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
        # todo: can I remove _keep_running?????
        self._keep_running = False


    def start(self):
        console_log('please','work')
        # annoying and weird way to get the remote user from the coroutine

        future = asyncio.Future()
        asyncio.async(self.get_remote_user(future), loop=self._loop)
        self._loop.run_until_complete(future)
        remote_user =  future.result()
        # remote_user = yield from future

        console_log('remote_user',remote_user)
        self._loop.call_soon(
            asyncio.async,
            self.check_osf(remote_user)
        )

    #todo: make this use make_request() as well
    @asyncio.coroutine
    def get_remote_user(self, future):
        print("checking projects of user with id {}".format(self.user_osf_id))
        url = 'https://staging2.osf.io:443/api/v2/users/{}/'.format(self.user_osf_id)
        resp = yield from self.make_request(url, get_json=True)
        future.set_result(resp['data'])

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
                # !!!!!fixme: this is a cheatcode!!!! for here, we are using path+item_type for here only for identifying purposes
                # fixme: doesn't work for when type/path is modified
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
                # console_log('self.get_id(sorted_combined_list[i])',self.get_id(sorted_combined_list[i]))
                # console_log('self.get_id(sorted_combined_list[i+1])',self.get_id(sorted_combined_list[i+1]))
                # console_log('both_exist',both_exist)

                # console_log('note in next two console_logs, one should be local, other should be remote',' in any order')
                # console_log('sorted_combined_list[i]',sorted_combined_list[i])
                # console_log('sorted_combined_list[i+1]',sorted_combined_list[i+1])

                # (local, remote)
                if isinstance(sorted_combined_list[i], dict):  # remote
                    new_tuple = (sorted_combined_list[i + 1], sorted_combined_list[i])
                elif isinstance(sorted_combined_list[i], Base):  # local
                    new_tuple = (sorted_combined_list[i], sorted_combined_list[i + 1])
                else:
                    raise TypeError('what the fudge did you pass in')
                # console_log('new_tuple',new_tuple)
                # add an extra 1 because both values should be added to tuple list
                i += 1
            elif isinstance(sorted_combined_list[i], dict):
                # console_log('self.get_id(sorted_combined_list[i])',self.get_id(sorted_combined_list[i]))
                # console_log('remote exists only','')
                # console_log('sorted_combined_list[i]',sorted_combined_list[i])
                new_tuple = (None, sorted_combined_list[i])
                # console_log('new_tuple',new_tuple)
            else:
                # console_log('self.get_id(sorted_combined_list[i])',self.get_id(sorted_combined_list[i]))
                # console_log('local exists only','')
                # console_log('sorted_combined_list[i]',sorted_combined_list[i])
                new_tuple = (sorted_combined_list[i], None)
                # console_log('new_tuple',new_tuple)
            local_remote_tuple_list.append(new_tuple)
            i += 1
        # console_log('local_remote_tuple_list',local_remote_tuple_list)
        for local, remote in local_remote_tuple_list:
            # console_log('remote', remote)
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
        projects_for_user_url = 'https://staging2.osf.io:443/api/v2/users/{}/nodes/'.format(remote_user_id)

        while self._keep_running:
            # get remote projects
            remote_projects = yield from self.get_all_paginated_members(projects_for_user_url)
            # todo: figure out how to actually get top level nodes. FOR NOW, I am just filtering by category = projects in response.
            temp = []
            for remote in remote_projects:
                if remote['category'] == 'project':
                    temp.append(remote)
            remote_projects = temp

            # get local projects
            local_projects = self.user.projects

            local_remote_projects = self.make_local_remote_tuple_list(local_projects, remote_projects)

            # BUG: I think there is a bug in the API.
            # If I delete a component online, it still shows up in the parent node's children list in the API.
            # I don't know how to handle this issue. For now, I will just ignore the fail when getting that deleted
            # nodes files.
            # ALSO: this probably means I can't delete nodes for now.
            for local, remote in local_remote_projects:
                # if local is None and remote is None:
                #     raise ValueError('whats going on bro????. both dont exist')
                # elif local is None:
                #     self.create_local_node()
                # elif remote is None:
                #     self.create_remote_node()
                # else:
                #     logs = self.get_logs(local.osf_id)

                # optimization: could check date modified of top level
                # and if not modified then don't worry about children
                yield from self.check_node(local, remote, local_parent_node=None, remote_parent_node=None)

            print('---------SHOULD HAVE ALL OSF FILES---------')

            yield from asyncio.sleep(RECHECK_TIME)
            # todo: figure out how we can prematuraly stop the sleep when user ends the application while sleeping

    @asyncio.coroutine
    def check_node(self, local_node, remote_node, local_parent_node, remote_parent_node):
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
        # elif local_node.locally_created and remote_node is None:
        #     yield from self.create_remote_node(local_node, remote_parent_node)
        #     # note: this should NOT return once create_remote_node is fixed.
        #     return
        # elif local_node.locally_created and remote_node is not None:
        #     raise ValueError('newly created local node already exists on server! WHY? broken!')
        # elif local_node.locally_deleted and remote_node is None:
        #     raise ValueError('local node was never on server for some reason. why? fixit!')
        # elif local_node.locally_deleted and remote_node is not None:
        #     yield from self.delete_remote_node(local_node, remote_node)
        #     # todo: delete_remote_node will have to handle making sure all children are deleted.
        #     return
        elif local_node is not None and remote_node is None:
            yield from self.delete_local_node(local_node)
            return
        elif local_node is not None and remote_node is not None:
            # todo: handle other updates to  node

            if local_node.title != remote_node['title']:
                # if self.local_is_newer(local_node, remote_node):
                #     yield from self.modify_remote_node(local_node, remote_node)
                # else:
                yield from self.modify_local_node(local_node, remote_node)

        # handle file_folders for node
        yield from self.check_file_folder(local_node, remote_node)

        # recursively handle node's children
        remote_children = yield from self.get_all_paginated_members(remote_node['links']['children']['related'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)
        for local, remote in local_remote_nodes:
            yield from self.check_node(local, remote, local_parent_node=local_node, remote_parent_node=remote_node)

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

            remote_children = yield from self.get_all_paginated_members(remote_file_folder['links']['related'])
            local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)
            for local, remote in local_remote_file_folders:
                yield from self._check_file_folder(local,
                                        remote,
                                        local_parent_file_folder=local_file_folder,
                                        local_node=local_node)
    @asyncio.coroutine
    def get_all_paginated_members(self, remote_url):
        remote_children = []

        # this is for the case that a new folder is created so does not have the proper links.
        if remote_url is None:
            return remote_children

        # try:
        resp = yield from self.make_request(remote_url, get_json=True)
        remote_children.extend(resp['data'])
        while resp['links']['next']:
            resp = yield from self.make_request(resp['links']['next'], get_json=True)
            remote_children.extend(resp['data'])
        # except:
        #     print('couldnt get subfolder and subfiles inside get_all_paginated_members for remote_url {}'.format(remote_url))
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
        self.save(new_node)

        # alert
        alerts.info(new_node.title, alerts.DOWNLOAD)

        # create local node folder on filesystem
        if not os.path.exists(new_node.path):
            os.makedirs(new_node.path)

        assert local_parent_node is None or (new_node in local_parent_node.components)
        return new_node
    # @asyncio.coroutine
    # def create_remote_node(self, local_node, remote_parent_node):
    #     print('create_remote_node')
    #     assert isinstance(local_node, Node)
    #     assert isinstance(remote_parent_node, dict) or (remote_parent_node is None)
    #     # parent_is_none implies new_node_is_project
    #     assert (remote_parent_node is not None) or (local_node.category == Node.PROJECT)
    #
    #     # alert
    #     alerts.info(local_node.title, alerts.UPLOAD)
    #
    #     data = {
    #         'title': local_node.title,
    #         # todo: allow users to choose other categories
    #         'category': 'project' if local_node.category == Node.PROJECT else 'other'
    #     }
    #
    #     if remote_parent_node:
    #         # component url
    #         assert local_node.category == Node.COMPONENT
    #         # fixme: THIS IS SOOOOOOOOOO  BROKEN!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #         # todo: make this part A LOT better once api does it.
    #
    #
    #         url = 'https://staging2.osf.io/{}/newnode/'.format(remote_parent_node['id'])
    #
    #         resp = yield from self.make_request(url, method='POST', data=data)
    #
    #         # request does not return json.
    #         # response does have url that contains the node if of the new node.
    #
    #         local_node.osf_id = resp.url.split('/')[-2]
    #         local_node.locally_created = False
    #         self.save(local_node)
    #
    #         # I think I need it in this case because I don't do anything with the response. no yield from resp.content or anything.
    #         resp.close()
    #
    #         # location header should have node id: https://staging2.osf.io/yz8eh/
    #         return
    #     else:
    #         # project url
    #         assert local_node.category == Node.PROJECT
    #         url = 'https://staging2.osf.io:443/api/v2/nodes/'
    #         resp = yield from self.make_request(url,method="POST", data=data, get_json=True)
    #
    #         remote_node = resp['data']
    #         local_node.osf_id = remote_node['id']
    #         local_node.locally_created = False
    #         self.save(local_node)
    #         return remote_node

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
        self.save(new_file_folder)
        if new_file_folder.name == 'LICENSE':
            console_log('new_file_folder (inside create_local_file_folder)', new_file_folder)

        # alert
        alerts.info(new_file_folder.name, alerts.DOWNLOAD)

        # create local file/folder on actual system
        if not os.path.exists(new_file_folder.path):
            if type == File.FILE:
                resp = yield from self.make_request(remote_file_folder['links']['self'])
                # with open(new_file_folder.path, 'wb') as fd:

                    # for chunk in resp.iter_content(2048):
                    #     fd.write(chunk)
                # todo: which is better? 1024 or 2048? Apparently, not much difference.
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

    # @asyncio.coroutine
    # def create_local_file_folder(self, remote_file_folder, local_parent_folder, local_node):
    # print('creating local file folder')
    #         assert remote_file_folder is not None
    #         assert remote_file_folder['type'] == 'files'
    #         assert isinstance(local_parent_folder, File) or local_parent_folder is None
    #         assert local_parent_folder is None or (local_parent_folder.type == File.FOLDER)
    #         assert isinstance(local_node, Node)
    #
    #
    #         #create local file folder in db
    #         type = File.FILE if remote_file_folder['item_type']=='file' else File.FOLDER
    #         new_file_folder = File(
    #             name=remote_file_folder['name'],
    #             type=type,
    #             osf_id=self.get_id(remote_file_folder),
    #             provider=remote_file_folder['provider'],
    #             osf_path=remote_file_folder['path'],
    #             user=self.user,
    #             parent=local_parent_folder,
    #             node=local_node)
    #         self.save(new_file_folder)
    #
    #         #create local file/folder on actual system
    #         local_filesystem_provider = make_provider(
    #             name='filesystem',
    #             auth={},
    #             credentials={},
    #             settings={'folder': new_file_folder.path} # determines where the file is downloaded to
    #         )
    #         #validates and returns a WaterButlerPath object
    #         path = yield from local_filesystem_provider.validate_path(remote_file_folder['name'])
    #         #wait until response is attained from given url.
    #         response = yield from self.make_request(url=remote_file_folder['links']['self'])
    #         if response.ok:
    #             # stream the file response to where it belongs on local file system
    #             yield from local_filesystem_provider.upload(
    #                 ResponseStreamReader(response, unsizable=True),
    #                 path,
    #             )
    #
    #         # if not os.path.exists(new_file_folder.path):
    #         #     if type == File.FILE:
    #         #         resp = requests.get(remote_file_folder['links']['self'], headers=self.headers)
    #         #         with open(new_file_folder.path, 'wb') as fd:
    #         #             for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
    #         #                 fd.write(chunk)
    #         #     elif type == File.FOLDER:
    #         #         os.makedirs(new_file_folder.path)
    #         #     else:
    #         #         raise ValueError('file type is unknown')
    #         return new_file_folder
    @asyncio.coroutine
    def create_remote_file_folder(self, local_file_folder, local_node):
        print('create_remote_file_folder')
        assert local_file_folder is not None
        assert isinstance(local_file_folder, File)
        assert local_node is not None
        assert isinstance(local_node, Node)
        assert local_file_folder.locally_created
        # assert remote_parent_folder_or_node is not None
        # assert isinstance(remote_parent_folder_or_node, dict)

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

        files_url = 'https://staging2-files.osf.io/file'  # todo: make this global

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

        remote_file_folder = resp

        # add additional fields to make it like a regular remote_file_folder
        remote_file_folder['type'] = 'files'
        remote_file_folder['item_type'] = remote_file_folder['kind']
        remote_file_folder['links'] = {}
        remote_file_folder['links']['related'] = None

        local_file_folder.osf_id = self.get_id(remote_file_folder)
        local_file_folder.osf_path = remote_file_folder['path']
        local_file_folder.locally_created = False
        self.save(local_file_folder)

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
        self.save(local_node)

        # alert
        alerts.info(local_node.title, alerts.MODIFYING)

        # modify local node on filesystem
        try:
            os.renames(old_path, local_node.path)
        except FileNotFoundError:
            print('renaming of file failed because file not there. inside modify_local_node')

    # @asyncio.coroutine
    # def modify_remote_node(self, local_node, remote_node):
    #     print('modify_remote_node')
    #     assert isinstance(local_node, Node)
    #     assert isinstance(remote_node, dict)
    #     assert remote_node['type'] == 'nodes'
    #     assert remote_node['id'] == local_node.osf_id
    #
    #     # alert
    #     alerts.info(local_node.title, alerts.MODIFYING)
    #
    #     # todo: add other fields here.
    #     data = {
    #         'title': local_node.title
    #     }
    #     resp = yield from self.make_request(remote_node['links']['self'],method="PATCH", data=data)
    #     resp.close()

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
        local_file_folder.name = remote_file_folder['title']
        self.save(local_file_folder)


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
        files_url = 'https://staging2-files.osf.io/file'  # todo: make this global



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
        url = 'https://staging2-files.osf.io/ops/move'
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
        self.save()

        # delete from local
        # todo: avoids_symlink_attacks: https://docs.python.org/3.4/library/shutil.html#shutil.rmtree.avoids_symlink_attacks
        # todo: make better error handling.
        shutil.rmtree(path, onerror=lambda a, b, c: print('local node not deleted because not exists.'))

    # todo: delete_remote_node will have to handle making sure all children are deleted.
    # @asyncio.coroutine
    # def delete_remote_node(self, local_node, remote_node):
    #     print('delete_remote_node')
    #     assert isinstance(local_node, Node)
    #     assert isinstance(remote_node, dict)
    #     assert local_node.osf_id == remote_node['id']
    #     assert local_node.locally_deleted
    #
    #     # alerts
    #     alerts.info(local_node.title, alerts.DELETING)
    #
    #     # recursively remove child nodes before you can remove current node, as per API.
    #     remote_children = yield from self.get_all_paginated_members(remote_node['links']['children']['related'])
    #     local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)
    #     for local, remote in local_remote_nodes:
    #         self.delete_remote_node(local, remote)
    #
    #     resp = yield from self.make_request(remote_node['links']['self'],method="DELETE")
    #     resp.close()
    #
    #     local_node.locally_deleted = False
    #     self.session.delete(local_node)
    #     self.save()

    @asyncio.coroutine
    def delete_local_file_folder(self, local_file_folder):
        print('delete_local_file_folder')
        assert isinstance(local_file_folder, File)

        path = local_file_folder.path
        file_folder_type = local_file_folder.type
        # delete model
        self.session.delete(local_file_folder)
        self.save()

        # alerts
        alerts.info(local_file_folder.name, alerts.DELETING)

        # delete from local
        if file_folder_type == File.FOLDER:
            # todo: avoids_symlink_attacks: https://docs.python.org/3.4/library/shutil.html#shutil.rmtree.avoids_symlink_attacks
            # todo: make better error handling.
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
        self.save()

    def save(self, item=None):
        if item:
            self.session.add(item)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise

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
            url = 'https://staging2-files.osf.io/revisions'
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

        # if remote['type'] == 'files' and remote['item_type'] == 'file':
        #     try:
        #
        #         remote_time = self.remote_to_local_datetime(remote['metadata']['modified'])
        #     # more general way to handle when remote['metadata']['modified'] is None
        #     except iso8601.ParseError:
        #         remote_time = None
        # else:
        #     remote_time = self.remote_to_local_datetime(remote['date_modified'])

        # if not remote_time:
        #     url = 'https://staging2-files.osf.io/revisions'
        #     params = {
        #         'path':local.osf_path,
        #         'provider':local.provider,
        #         'nid':local.node.osf_id,
        #     }
        #     resp = yield from self.make_request(url, params=params, get_json=True)
        #     time_modified = resp['data'][0]['modified']
        #     for revision in resp['data']:
        #         assert self.remote_to_local_datetime(time_modified) >= self.remote_to_local_datetime(revision['modified'])
        #     remote_time = self.remote_to_local_datetime(time_modified)
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
        elif 400 <= response.status < 600 :
            content = yield from response.read()
            raise ConnectionError('failed {} request {} with expected response code(s) {}. response.content={}'.format(method, url, expects,content ))
        if get_json:
            json_response = yield from response.json()
            return json_response

        return response

    def local_remote_etag_are_diff(self, local_file, remote_file):
        assert local_file is not None
        assert remote_file is not None
        assert local_file.osf_path == remote_file['path']
        assert local_file.type == File.FILE
        assert remote_file['type'] == 'files'
        assert remote_file['item_type'] == 'file'

        wb_data = self.get_wb_data(local_file, remote_file)
        assert 'etag' in wb_data

        return local_file.etag != wb_data['etag']

    # def get_wb_data(self, local_file_folder, remote_file_folder):
    #     """
    #     This function is meant to be called during modifications, thus can assume both local_file_folder and remote_file_folder exist
    #     """
    #     assert local_file_folder is not None
    #     assert remote_file_folder is not None
    #     assert local_file_folder.osf_path == remote_file_folder['path']
    #     # if local_file_folder.parent:
    #     #     NOTE: only need 1 level up!!!!!! thats how path works in this case.
    #     #     path = local_file_folder.parent.osf_path + local_file_folder.name
    #     # else:
    #     #     path = '/{}'.format(local_file_folder.name)
    #     path = local_file_folder.osf_path
    #     params = {
    #         'path': path,
    #         'nid': local_file_folder.node.osf_id,
    #         'provider': local_file_folder.provider,
    #     }
    #     params_string = '&'.join([str(k) + '=' + str(v) for k, v in params.items()])
    #     WB_DATA_URL = 'https://staging2-files.osf.io/data'
    #     file_url = WB_DATA_URL + '?' + params_string
    #     print(file_url)
    #     headers = {
    #         'Origin': 'https://staging2.osf.io',
    #         'Accept-Encoding': 'gzip, deflate, sdch',
    #         'Accept-Language': 'en-US,en;q=0.8',
    #         'Authorization': 'Bearer {}'.format(self.user.oauth_token),
    #         'Accept': 'application/json, text/*',
    #         'Referer': 'https://staging2.osf.io/{}/'.format(local_file_folder.node_id),
    #         'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
    #         'Connection': 'keep-alive'
    #     }
    #
    #     resp = requests.get(file_url, headers=headers)
    #     if resp.ok:
    #         return resp.json()['data']
    #     else:
    #         raise ValueError('waterbutler data for file {} not attained: {}'.format(local_file_folder.name, resp.content))

    # def get_logs(self, node_id):
    #     headers = {
    #         'Cookie': 'osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; '
    #     }
    #     url = 'https://staging2.osf.io/api/v1/project/{}/log/'.format(node_id)
    #     resp = requests.get(url, headers=headers)
    #     if resp.ok:
    #         return resp.json()
    #
    # def good_response(self, response):
    #     return (response.status < 300) and (response.status >= 200)

def console_log(variable_name, variable_value):
    print("DEBUG: {}: {}".format(variable_name, variable_value))