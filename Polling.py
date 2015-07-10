__author__ = 'himanshu'
import json
import os
import asyncio
import requests
from queue import Queue, Empty
from datetime import datetime
from threading import Thread
from models import User, Node, File, create_engine, sessionmaker, get_session, Base
from sqlalchemy.orm import scoped_session
from sqlalchemy.pool import SingletonThreadPool
import iso8601
import pytz
import shutil
import logging
from waterbutler.core.utils import make_provider
from waterbutler.core.streams import ResponseStreamReader
import aiohttp
import alerts

# this code is for ssl errors that occur due to requests module:
# http://stackoverflow.com/questions/14102416/python-requests-requests-exceptions-sslerror-errno-8-ssl-c504-eof-occurred
import ssl
from functools import wraps
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar

ssl.wrap_socket = sslwrap(ssl.wrap_socket)


RECHECK_TIME = 5 # in seconds

class Poll(object):
    def __init__(self, user_osf_id, loop):
        super().__init__()
        self._keep_running = True
        self.user_osf_id = user_osf_id
        self.session = get_session()
        self.user = self.session.query(User).filter(User.osf_id == user_osf_id).one() # todo: does passing in user directly break things?

        #todo: make headers be from a remote desktop client
        #todo: make a method make_request that handles putting in header. puts in Auth. streams. async.

        self.headers =  {
            # 'Host': 'staging2.osf.io',
            # 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'Referer': 'https://staging2.osf.io/api/v2/docs/',
            # 'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
            #this last one is key!
            'Cookie':'_ga=GA1.2.1042569900.1436205463; osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _pk_id.1.2840=841d2b69a87afbce.1436271936.8.1436340402.1436338347.; _pk_ses.1.2840=*',
            #this one is key for files
            'Authorization' : 'Bearer {}'.format(self.user.oauth_token)
        }

        self._loop = loop or asyncio.get_event_loop()


    def stop(self):
        #todo: can I remove _keep_running?????
        self._keep_running = False
        self._loop.stop()
        self._loop.close()
        # self._loop.close()

    def start(self):
        remote_user = self.get_remote_user()
        self._loop.call_soon(self.check_osf,remote_user)



    def get_remote_user(self):
        print("checking projects of user with id {}".format(self.user_osf_id))
        resp = requests.get('https://staging2.osf.io:443/api/v2/users/{}/'.format(self.user_osf_id), headers=self.headers)
        if resp.ok:
            return resp.json()['data']
        else:
            raise ValueError('could not get remote user with osf_id {}:{}'.format(self.user_osf_id, resp.content))


    def get_id(self, item):
        """
        This function determines the rules to get the id for a local or remote representation of nodes/files.
        The ways to get the id differ based on the input item type:
            local node -> osf_id ( this is node id (nid) on the OSF )
            local file -> hash(node.osf_id, provider name, osf path)
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
                return str(hash(item['path'] + item['item_type']))
            else:
                raise ValueError(item['type'] +'is not handled')
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
            if i+1 < len(sorted_combined_list) and \
                            self.get_id(sorted_combined_list[i]) \
                            == \
                            self.get_id(sorted_combined_list[i+1]):
                # (local, remote)
                if isinstance(sorted_combined_list[i], dict): # remote
                    new_tuple = (sorted_combined_list[i+1],sorted_combined_list[i])
                elif isinstance(sorted_combined_list[i], Base): # local
                    new_tuple = (sorted_combined_list[i],sorted_combined_list[i+1])
                else:
                    raise TypeError('what the fudge did you pass in')
                i += 1 #add an extra 1 because both values should be added to tuple list
            elif isinstance(sorted_combined_list[i], dict):
                new_tuple = (None,sorted_combined_list[i])
            else:
                new_tuple = (sorted_combined_list[i], None)
            local_remote_tuple_list.append( new_tuple )
            i += 1
        for local, remote in local_remote_tuple_list:
            assert isinstance(local, Base) or local is None
            assert isinstance(remote, dict) or remote is None
            if isinstance(local, Base) and isinstance(remote, dict):
                assert local.osf_id == self.get_id(remote)

        return local_remote_tuple_list


    #Check

    def check_osf(self,remote_user):
        print('check_osf')
        assert isinstance(remote_user,dict)
        assert remote_user['type']=='users'


        remote_user_id = remote_user['id']
        projects_for_user_url = 'https://staging2.osf.io:443/api/v2/users/{}/nodes/'.format(remote_user_id)


        if self._keep_running:
            #get remote projects
            remote_projects = self.get_all_paginated_members(projects_for_user_url)


            #todo: figure out how to actually get top level nodes. FOR NOW, I am just filtering by category = projects in response.
            temp = []
            for remote in remote_projects:
                if remote['category'] == 'project':
                    temp.append(remote)
            remote_projects = temp

            #get local projects
            local_projects = self.user.projects

            local_remote_projects = self.make_local_remote_tuple_list(local_projects, remote_projects)
            # BUG: I think there is a bug in the API.
            # If I delete a component online, it still shows up in the parent node's children list in the API.
            # I don't know how to handle this issue. For now, I will just ignore the fail when getting that deleted
            # nodes files.
            # ALSO: this probably means I can't delete nodes for now.
            for local, remote in local_remote_projects:
                # optimization: could check date modified of top level
                # and if not modified then don't worry about children
                self.check_node(local, remote, local_parent_node=None, remote_parent_node=None)


            print('---------SHOULD HAVE ALL OSF FILES---------')

            self._loop.call_later(RECHECK_TIME, self.check_osf, remote_user)
            #todo: figure out how we can prematuraly stop the sleep when user ends the application while sleeping
            # print('SLEEPING FOR {} seconds...'.format(RECHECK_TIME))



    def check_node(self,local_node, remote_node, local_parent_node, remote_parent_node):
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
        assert (local_node is not None) or (remote_node is not None) # both shouldnt be none.
        assert (local_parent_node is None) or isinstance(local_parent_node, Node)


        if local_node is None:
            local_node = self.create_local_node(remote_node,local_parent_node)
        elif local_node.locally_created and remote_node is None:
            remote_node = self.create_remote_node(local_node,remote_parent_node)
            #note: this should NOT return once create_remote_node is fixed.
            return
        elif local_node.locally_created and remote_node is not None:
            raise ValueError('newly created local node already exists on server! WHY? broken!')
        elif local_node.locally_deleted and remote_node is None:
            raise ValueError('local node was never on server for some reason. why? fixit!')
        elif local_node.locally_deleted and remote_node is not None:
            self.delete_remote_node(local_node, remote_node)
            #todo: delete_remote_node will have to handle making sure all children are deleted.
            return
        elif local_node is not None and remote_node is None:
            self.delete_local_node(local_node)
            return
        elif local_node is not None and remote_node is not None:
            # todo: handle other updates to  node

            if local_node.title != remote_node['title']:
                if self.local_is_newer(local_node, remote_node):
                    self.modify_remote_node(local_node, remote_node)
                else:
                    self.modify_local_node(local_node, remote_node)
        else:
            raise ValueError('in some weird state. figure it out.')

        #handle file_folders for node
        self.check_file_folder(local_node, remote_node)

        #recursively handle node's children
        remote_children = self.get_all_paginated_members(remote_node['links']['children']['related'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)
        for local, remote in local_remote_nodes:
            self.check_node(local, remote, local_parent_node=local_node, remote_parent_node=remote_node)

    #todo: determine if we just want osfstorage or also other things
    def check_file_folder(self, local_node, remote_node):
        print('checking file_folder')

        remote_node_files = self.get_all_paginated_members(remote_node['links']['files']['related'])
        local_remote_files = self.make_local_remote_tuple_list(local_node.top_level_file_folders, remote_node_files)

        for local, remote in local_remote_files:
            self._check_file_folder(local, remote, local_parent_file_folder=None,remote_parent_folder=None, local_node=local_node )

    def _check_file_folder(self,local_file_folder,remote_file_folder, local_parent_file_folder, remote_parent_folder,local_node):
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
        assert (local_file_folder is not None) or (remote_file_folder is not None) # both shouldnt be None.

        print('checking file_folder internal')
        if local_file_folder is None:
            local_file_folder = self.create_local_file_folder(remote_file_folder, local_parent_file_folder, local_node)
        elif local_file_folder.locally_created and remote_file_folder is None:
            #todo: this is broken for now. Need to figure out a diff way to do this.
            remote_file_folder = self.create_remote_file_folder(local_file_folder, local_node)
            return
        elif local_file_folder.locally_created and remote_file_folder is not None:
            raise ValueError('newly created local file_folder was already on server for some reason. why? fixit!')
        elif local_file_folder.locally_deleted and remote_file_folder is None:
            raise ValueError('local file_folder was never on server for some reason. why? fixit!')
        elif local_file_folder.locally_deleted and remote_file_folder is not None:
            self.delete_remote_file_folder(local_file_folder, remote_file_folder)
            return
        elif local_file_folder is not None and remote_file_folder is None:
            self.delete_local_file_folder(local_file_folder)
            return
        elif local_file_folder is not None and remote_file_folder is not None:
            # todo: this is broken for now as well. Need additional functionalities on server for this.
            # todo: diff way to do this is also good.
            possibly_new_remote_file_folder = self.modify_file_folder_logic(local_file_folder, remote_file_folder)
            if possibly_new_remote_file_folder:
                remote_file_folder = possibly_new_remote_file_folder
        else:
            raise ValueError('in some weird state. figure it out.')

        assert local_file_folder is not None
        assert remote_file_folder is not None

        #recursively handle folder's children
        if local_file_folder.type == File.FOLDER:

            remote_children = self.get_all_paginated_members(remote_file_folder['links']['related'])
            local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)
            for local, remote in local_remote_file_folders:
                self._check_file_folder(local, remote, local_parent_file_folder=local_file_folder, remote_parent_folder=remote_file_folder, local_node=local_node)

    def get_all_paginated_members(self, remote_url):
        remote_children = []

        # this is for the case that a new folder is created so does not have the proper links.
        if remote_url is None:
            return remote_children

        try:
            resp = requests.get(remote_url, headers = self.headers).json()
            remote_children.extend(resp['data'])
            while resp['links']['next'] != None:
                resp = requests.get(resp['links']['next'], headers=self.headers).json()
                remote_children.extend(resp['data'])
        except:

            print('couldnt get subfolder and subfiles. no permission.')
        return remote_children


    #Create

    def create_local_node(self, remote_node, local_parent_node):
        print('create_local_node')
        assert isinstance(remote_node, dict)
        assert remote_node['type'] == 'nodes'
        assert isinstance(local_parent_node,Node) or local_parent_node is None

        #create local node in db
        category = Node.PROJECT if remote_node['category']=='project' else Node.COMPONENT
        new_node = Node(
            title=remote_node['title'],
            category=category,
            osf_id=remote_node['id'],
            user=self.user,
            parent=local_parent_node
        )
        self.save(new_node)

        #alert
        alerts.info(new_node.title, alerts.DOWNLOAD)

        #create local node folder on filesystem
        if not os.path.exists(new_node.path):
            os.makedirs(new_node.path)

        assert local_parent_node is None or (new_node in local_parent_node.components)
        return new_node


    def create_remote_node(self, local_node, remote_parent_node):
        print('create_remote_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_parent_node, dict) or (remote_parent_node is None)
        assert (remote_parent_node is not None) or (local_node.category == Node.PROJECT) # parent_is_none implies new_node_is_project

        # alert
        alerts.info(local_node.title, alerts.UPLOAD)

        data={
            'title': local_node.title,
            # todo: allow users to choose other categories
            'category': 'project' if local_node.category == Node.PROJECT else 'other'
        }

        if remote_parent_node:
            # component url
            assert local_node.category == Node.COMPONENT
            #fixme: THIS IS SOOOOOOOOOO  BROKEN!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #todo: make this part A LOT better once api does it.
            console_log('create remote node','creating component')

            url = 'https://staging2.osf.io/{}/newnode/'.format(remote_parent_node['id'])
            console_log('url',url)
            resp = requests.post(url, data=data, headers=self.headers)
            # console_log('resp.content',resp.content)

            # request does not return json.
            # request does have location field that does have node id of the new node.
            if resp.ok:
                console_log('resp.headers',resp.headers)
                # location header should have node id: https://staging2.osf.io/yz8eh/
                # nid = resp.headers['Location'].split('/')[-2]

                # console_log('nid',nid)
                # remote_node = requests.get('https://staging2.osf.io:443/api/v2/nodes/{}/'.format(nid), headers=self.headers)
                # console_log('remote_node',remote_node)

                return
            else:
                raise ValueError('remote node not created:{}'.format(resp.content))
        else:
            # project url
            assert local_node.category == Node.PROJECT
            url = 'https://staging2.osf.io:443/api/v2/nodes/'
            resp = requests.post(url, data=data, headers=self.headers)

            if resp.ok:
                remote_node = resp.json()['data']
                local_node.osf_id = remote_node['id']
                local_node.locally_created = False
                self.save(local_node)
                return remote_node
            else:
                raise ValueError('remote node not created:{}'.format(resp.content))

    def create_local_file_folder(self, remote_file_folder, local_parent_folder, local_node):
        print('creating local file folder')
        assert remote_file_folder is not None
        assert remote_file_folder['type'] == 'files'
        assert isinstance(local_parent_folder, File) or local_parent_folder is None
        assert local_parent_folder is None or (local_parent_folder.type == File.FOLDER)
        assert isinstance(local_node, Node)


        #create local file folder in db
        type = File.FILE if remote_file_folder['item_type']=='file' else File.FOLDER
        new_file_folder = File(
            name=remote_file_folder['name'],
            type=type,
            osf_id=self.get_id(remote_file_folder),
            provider=remote_file_folder['provider'],
            osf_path=remote_file_folder['path'],
            user=self.user,
            parent=local_parent_folder,
            node=local_node)
        self.save(new_file_folder)

        # alert
        alerts.info(new_file_folder.name, alerts.DOWNLOAD)

        #create local file/folder on actual system
        if not os.path.exists(new_file_folder.path):
            if type == File.FILE:
                resp = requests.get(remote_file_folder['links']['self'], headers=self.headers)
                with open(new_file_folder.path, 'wb') as fd:
                    for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                        fd.write(chunk)
            elif type == File.FOLDER:
                os.makedirs(new_file_folder.path)
            else:
                raise ValueError('file type is unknown')
        return new_file_folder
    # @asyncio.coroutine
    # def create_local_file_folder(self, remote_file_folder, local_parent_folder, local_node):
    #         print('creating local file folder')
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

    def create_remote_file_folder(self, local_file_folder, local_node):
        print('create_remote_file_folder')
        assert local_file_folder is not None
        assert isinstance(local_file_folder, File)
        assert local_node is not None
        assert isinstance(local_node, Node)
        assert local_file_folder.locally_created == True
        # assert remote_parent_folder_or_node is not None
        # assert isinstance(remote_parent_folder_or_node, dict)

        # alert
        alerts.info(local_file_folder.name, alerts.DOWNLOAD)


        if local_file_folder.parent:
            #fixme: only handles 1 level up !!!!!
            path = local_file_folder.parent.osf_path + local_file_folder.name
        else:
            path = '/{}'.format(local_file_folder.name)
        params = {
            #fixme: path is probably incorrect. fix it.
            'path':path,
            'provider':local_file_folder.provider,
            'nid': local_node.osf_id
        }
        # print(params)
        params_string = '&'.join([k+'='+v for k,v in params.items()])
        FILES_URL ='https://staging2-files.osf.io/file'
        file_url = FILES_URL + '?' + params_string
        # print(file_url)

        if local_file_folder.type == File.FOLDER:
            resp = requests.post(file_url, headers=self.headers )
        elif local_file_folder.type == File.FILE:
            #https://github.com/kennethreitz/requests/issues/2639 issue when file has non-ascii characters.
            try:
                #fixme: UnicodeDecodeError occured once. WHY?????? requests should handle it. idk.
                files = {'file':open(local_file_folder.path)}
                resp = requests.put(file_url, headers=self.headers, files=files) # try 1
            except UnicodeDecodeError:
                files = {'file':open(local_file_folder.path).read()}
                resp = requests.put(file_url, headers=self.headers, files=files) # try 2

        if resp.ok:
            remote_file_folder = resp.json()

            #add additional fields to make it like a regular remote_file_folder
            remote_file_folder['type'] = 'files'
            remote_file_folder['item_type'] = remote_file_folder['kind']
            remote_file_folder['links'] = {}
            remote_file_folder['links']['related'] = None

            local_file_folder.osf_id = self.get_id(remote_file_folder)
            local_file_folder.osf_path = remote_file_folder['path']
            local_file_folder.locally_created = False
            self.save(local_file_folder)

            return remote_file_folder
        else:
           raise ValueError('file_folder not created on remote server properly:{}'.format(resp.content))

    #Modify

    def modify_local_node(self, local_node, remote_node):
        print('modify_local_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, dict)
        assert remote_node['type']=='nodes'
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
            print('renaming of file failed because file not there.')
    def modify_remote_node(self, local_node, remote_node):
        print('modify_remote_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, dict)
        assert remote_node['type']=='nodes'
        assert remote_node['id'] == local_node.osf_id

        # alert
        alerts.info(local_node.title, alerts.MODIFYING)


        #todo: add other fields here.
        data = {
            'title': local_node.title
        }
        resp = requests.patch(remote_node['links']['self'],data=data, headers=self.headers)
        if not resp.ok:
            raise ValueError('remote node not modified:{}'.format(resp.content))

    # todo: handle other updates to file_folder
    def modify_file_folder_logic(self, local_file_folder, remote_file_folder):
        updated_remote_file_folder = None
        if local_file_folder.type == File.FILE:
            #todo: hash? etag doesnt work. etag = hash(version, path) which is not helpful. already handle path. version does not match with local.
            # if self.local_remote_etag_are_diff(local_file_folder, remote_file_folder):
            if self.local_is_newer(local_file_folder, remote_file_folder):
                pass #todo: broken
                updated_remote_file_folder = self.modify_remote_file_folder(local_file_folder, remote_file_folder)
            elif self.remote_is_newer(local_file_folder, remote_file_folder):
                self.modify_local_file_folder(local_file_folder, remote_file_folder)

        elif local_file_folder.type == File.FOLDER:
            if local_file_folder.name != remote_file_folder['name']:
                #fixme: how to determine which is most recent version of folder??? perhaps just take stat? yea.
                #fixme: we do not have size or date modified of remote folder.
                #fixme: for now, we just always push to remote
                # if self.local_is_newer(local_file_folder, remote_file_folder):
                #     pass #todo: broken
                print('DEBUG:modify_file_folder_logic:local_file_folder.name:{}'.format(local_file_folder.name))
                updated_remote_file_folder = self.modify_remote_file_folder(local_file_folder, remote_file_folder)
                # elif self.remote_is_newer(local_file_folder, remote_file_folder):
                #     self.modify_local_file_folder(local_file_folder, remote_file_folder)

        # want to have the remote file folder continue to be the most recent version.
        return updated_remote_file_folder


    def modify_local_file_folder(self, local_file_folder, remote_file_folder):
        print('modify_local_file_folder')
        assert isinstance(local_file_folder, File)
        assert isinstance(remote_file_folder, dict)
        assert remote_file_folder['type']=='files'
        assert remote_file_folder['path'] == local_file_folder.osf_path

        # alerts
        alerts.info(local_file_folder.name, alerts.MODIFYING)

        if local_file_folder.type == File.FOLDER:
            old_path = local_file_folder.path
            # update model
            local_file_folder.name = remote_file_folder['title']
            self.save(local_file_folder)

            # update local file system
            try:
                os.renames(old_path, local_file_folder.path)
            except FileNotFoundError:
                print('folder not modified because doesnt exist')
        elif local_file_folder.type == File.FILE:
            #todo: need the db file to be updated to show that its timestamp is in fact updated.
            #todo: can read this: http://docs.sqlalchemy.org/en/improve_toc/orm/events.html
            #update model
            # self.save(local_file_folder) # todo: this does NOT actually update the local_file_folder timestamp


            #update local file system
            try:
                resp = requests.get(remote_file_folder['links']['self'], headers=self.headers)
                with open(local_file_folder.path, 'wb') as fd:
                    for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                        fd.write(chunk)
            except FileNotFoundError: #file was deleted locally.
                print('file not updated locally because it doesnt exist')

    def modify_remote_file_folder(self, local_file_folder, remote_file_folder):
        print('modify_remote_file_folder. NOTE: this calls create_remote_file_folder and delete_file_folder')
        assert isinstance(local_file_folder, File)

        # alerts
        alerts.info(local_file_folder.name, alerts.MODIFYING)

        new_remote_file_folder = remote_file_folder

        if local_file_folder.type == File.FILE:
            local_node = local_file_folder.node
            #handle modifying remote file folder by deleting then reuploading local file_folder
            # self.delete_remote_file_folder(local_file_folder, remote_file_folder)
            #fixme: create_remote_file_folder expects the local_file_folder to be .locally_created. thus make it true for now
            local_file_folder.locally_created= True
            new_remote_file_folder = self.create_remote_file_folder(local_file_folder, local_node)
        else:
            # OSF allows you to manually rename a folder. Use That.
            url = 'https://staging2-files.osf.io/ops/move'
            data = {
               'rename': local_file_folder.name,
               'conflict':'replace',
               'source':{
                   'path':local_file_folder.osf_path,
                   'provider':local_file_folder.provider,
                   'nid':local_file_folder.node.osf_id
               },
               'destination':{
                   'path':local_file_folder.parent.osf_path,
                   'provider':local_file_folder.provider,
                   'nid':local_file_folder.node.osf_id
               }
            }

            resp = requests.post(url, headers=self.headers, data=json.dumps(data))
            if resp.ok:
                # get the updated remote folder
                print('debug: resp.content:{}'.format(resp.content))
                # inner_response = requests.get(remote_file_folder['links']['self'], headers=self.headers).json()
                #we know exactly what changed, so its faster to just change the remote dictionary rather than making a new api call.
                print(new_remote_file_folder)
                new_remote_file_folder['name'] = data['rename']
                print(new_remote_file_folder)

            else:
                raise ValueError('folder not renamed: {}'.format(resp.content))
            """
            'https://staging2-files.osf.io/ops/move'
            -H 'Authorization: Bearer eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ'
            -H 'Origin: https://staging2.osf.io'
            -H 'Accept-Encoding: gzip, deflate'
            -H 'Accept-Language: en-US,en;q=0.8'
            -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.130 Safari/537.36'
            -H 'Content-Type: Application/json'
            -H 'Accept: */*'
            -H 'Referer: https://staging2.osf.io/mk26q/'
            -H 'Connection: keep-alive'
            --data-binary '{"rename":"myfolderrock","conflict":"replace","source":{"path":"/559d6814404f7702f8fae9cf/","provider":"osfstorage","nid":"mk26q"},"destination":{"path":"/","provider":"osfstorage","nid":"mk26q"}}' --compressed
            """

        return new_remote_file_folder



    #Delete

    def delete_local_node(self, local_node):
        print('delete_local_node')
        assert isinstance(local_node, Node)

        path = local_node.path

        # alerts
        alerts.info(local_node.title, alerts.DELETING)

        #delete model
        self.session.delete(local_node)
        self.save()

        #delete from local
        #todo: avoids_symlink_attacks: https://docs.python.org/3.4/library/shutil.html#shutil.rmtree.avoids_symlink_attacks
        #todo: make better error handling.
        shutil.rmtree(path, onerror=lambda a,b,c:print('local node not deleted because not exists.'))


    #todo: delete_remote_node will have to handle making sure all children are deleted.
    def delete_remote_node(self, local_node, remote_node):
        print('delete_remote_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, dict)
        assert local_node.osf_id == remote_node['id']
        assert local_node.locally_deleted == True

        # alerts
        alerts.info(local_node.title, alerts.DELETING)

        # tail recursion to remove child remote nodes before you can remove current top level remote node.
        remote_children = self.get_all_paginated_members(remote_node['links']['children']['related'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)
        for local, remote in local_remote_nodes:
            self.delete_remote_node(local, remote)

        resp = requests.delete(remote_node['links']['self'], headers=self.headers)
        if resp.ok:
            local_node.locally_deleted = False
            self.session.delete(local_node)
            self.save()
        else:
            raise ValueError('delete remote node failed: {}'.format(resp.content))

    def delete_local_file_folder(self, local_file_folder):
        print('delete_local_file_folder')
        assert isinstance(local_file_folder, File)


        path = local_file_folder.path
        file_folder_type = local_file_folder.type
        #delete model
        self.session.delete(local_file_folder)
        self.save()


        # alerts
        alerts.info(local_file_folder.name, alerts.DELETING)

        #delete from local
        if file_folder_type == File.FOLDER:
            #todo: avoids_symlink_attacks: https://docs.python.org/3.4/library/shutil.html#shutil.rmtree.avoids_symlink_attacks
            #todo: make better error handling.
            shutil.rmtree(path, onerror=lambda a,b,c:print('delete local folder failed because folder already deleted'))
        else:
            try:
                os.remove(path)
            except FileNotFoundError:
                print('file not deleted because does not exist on local filesystem')

    def delete_remote_file_folder(self, local_file_folder, remote_file_folder):
        print('delete_remote_file_folder')
        assert local_file_folder is not None
        assert remote_file_folder is not None
        assert local_file_folder.osf_id == self.get_id(remote_file_folder)
        assert local_file_folder.locally_deleted == True

        # alerts
        alerts.info(local_file_folder.name, alerts.DELETING)

        url = remote_file_folder['links']['self'].split('&cookie=')[0]
        print("DEBUG: url in delete_remote_file_folder:{}".format(url))
        resp = requests.delete(url, headers=self.headers)
        if resp.ok:
            local_file_folder.deleted = False
            self.session.delete(local_file_folder)
            self.save()
        else:
            raise ValueError('delete remote file folder failed:{}'.format(resp.content))



    def save(self, item=None):
        if item:
            self.session.add(item)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise

    # todo: determine proper logic for when to update local/remote. (specifically for files based on datetime for now.)
    def _get_local_remote_times(self, local, remote):
        assert local is not None
        assert remote is not None
        assert isinstance(local, Base)
        assert isinstance(remote, dict)

        local_time = local.date_modified.replace(tzinfo=pytz.utc)
        if remote['type'] == 'files' and remote['item_type'] == 'file':
            try:
                remote_time = self.remote_to_local_datetime(remote['metadata']['modified'])
            except iso8601.ParseError: # more general way to handle when remote['metadata']['modified'] is None
                remote_time = None
        # elif remote['type']=='files' and remote['item_type'] == 'folder':
        #     remote_time = None
        else:
            print('DEBUG: _get_local_remote_times:remote:{}'.format(str(remote)))
            remote_time = self.remote_to_local_datetime(remote['date_modified'])
        return (local_time, remote_time)

    def local_is_newer(self, local, remote):
        local_time, remote_time = self._get_local_remote_times(local, remote)

        # fixme: for now, if remote is None, then most recent is whichever one is bigger.
        if remote_time is None:
            if remote['type'] == 'files' and remote['item_type']=='file':
                print('DEBUG: local_is_newer: look at this as well: local.size:{}, remote[metadata][size]:{}'.format(local.size, remote['metadata']['size']))
                return local.size > remote['metadata']['size']

        return local_time > remote_time

    def remote_is_newer(self, local, remote):
        local_time, remote_time = self._get_local_remote_times(local, remote)
        # fixme: what should remote_time is None do???
        if remote_time is None:
            if remote['type'] == 'files' and remote['item_type']=='file':
                print('DEBUG: remote_is_newer: look at this as well: local.size:{}, remote[metadata][size]:{}'.format(local.size, remote['metadata']['size']))
                return local.size < remote['metadata']['size']
        return local_time < remote_time

    def remote_to_local_datetime(self,remote_utc_time_string ):
        """convert osf utc time string to a proper datetime (with utc timezone).
            throws iso8601.ParseError. Handle as needed.
        """
        return iso8601.parse_date(remote_utc_time_string)

    @asyncio.coroutine
    def make_request(self,url,method='GET'):

        yield aiohttp.request(
            method,
            url,
            headers={'Authorization': 'Bearer {}'.format(self.user.oauth_token)}
        )

    def local_remote_etag_are_diff(self, local_file, remote_file):
        assert local_file is not None
        assert remote_file is not None
        assert local_file.osf_path == remote_file['path']
        assert local_file.type == File.FILE
        assert remote_file['type']=='files'
        assert remote_file['item_type'] == 'file'

        wb_data = self.get_wb_data(local_file, remote_file)
        assert 'etag' in wb_data

        return local_file.etag != wb_data['etag']

    def get_wb_data(self, local_file_folder, remote_file_folder):
        """
        This function is meant to be called during modifications, thus can assume both local_file_folder and remote_file_folder exist
        """
        assert local_file_folder is not None
        assert remote_file_folder is not None
        assert local_file_folder.osf_path == remote_file_folder['path']
        # if local_file_folder.parent:
        #     NOTE: only need 1 level up!!!!!! thats how path works in this case.
            # path = local_file_folder.parent.osf_path + local_file_folder.name
        # else:
        #     path = '/{}'.format(local_file_folder.name)
        path = local_file_folder.osf_path
        params = {
            'path':path,
            'nid':local_file_folder.node.osf_id,
            'provider':local_file_folder.provider,
        }
        params_string = '&'.join([str(k)+'='+str(v) for k,v in params.items()])
        WB_DATA_URL ='https://staging2-files.osf.io/data'
        file_url = WB_DATA_URL + '?' + params_string
        print(file_url)
        headers =  {
                'Origin': 'https://staging2.osf.io',
                'Accept-Encoding': 'gzip, deflate, sdch',
                'Accept-Language': 'en-US,en;q=0.8',
                'Authorization' : 'Bearer {}'.format(self.user.oauth_token),
                'Accept': 'application/json, text/*',
                'Referer': 'https://staging2.osf.io/{}/'.format(local_file_folder.node_id),
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',

                # 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                # 'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
                #this last one is key!
                # 'Cookie':'_ga=GA1.2.1042569900.1436205463; osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _pk_id.1.2840=841d2b69a87afbce.1436271936.8.1436340402.1436338347.; _pk_ses.1.2840=*',
                #this one is key for files

                'Connection':'keep-alive'
            }

        resp = requests.get(file_url, headers=headers)
        if resp.ok:
            return resp.json()['data']
        else:
            raise ValueError('waterbutler data for file {} not attained: {}'.format(local_file_folder.name, resp.content))



def console_log(variable_name, variable_value):
    print("DEBUG: {}: {}".format(variable_name, variable_value))

