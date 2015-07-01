__author__ = 'himanshu'
import requests
import os

__author__ = 'himanshu'
import requests
import os
import asyncio

from queue import Queue, Empty
from datetime import datetime
from threading import Thread
from models import User, Node, File, create_engine, sessionmaker, get_session, Base
from sqlalchemy.orm import scoped_session
from sqlalchemy.pool import SingletonThreadPool
import iso8601
import requests
import shutil
import logging
RECHECK_TIME = 5

class Poll(object):
    def __init__(self, user_osf_id, loop):
        super().__init__()
        self._keep_running = True
        self.user_osf_id = user_osf_id
        self.session = get_session()
        self.headers = headers = {
            'Host': 'staging2.osf.io',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://staging2.osf.io/api/v2/docs/',
            'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
            #this last one is key!
            # 'Cookie':'_pk_id.1.2840=5d8268ce2f65679d.1435256429.15.1435688575.1435688083.; csrftoken=qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK; _pk_id.1.0e8b=3e752283c198c4ce.1435342348.1.1435342354.1435342348.; _pk_ref.1.0e8b=%5B%22%22%2C%22%22%2C1435342348%2C%22https%3A%2F%2Fstaging2.osf.io%2F2r67q%2F%22%5D; _pk_ses.1.2840=*; osf_staging2=5592dcf7404f776a0257c302.7F4S2OqxsOcaHceTbpeTFUkXHX0',
            #this one is key for files
            'Authorization' : 'Bearer eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLlktRFZrazctVi05RUZQVHJSRFN6dFEuN3hYUUthNkl5dXFKQ2o4bW5NQWY0dGhYTmw2SFdCdEJMdmZEazY4ZnBpYzZ3d3F5NnJqcjA0V1JxQ2E4VVBWYUNzMm01a0hMemNYVzh0ZFl6VjB1UUlrSnpyenVkTVRxODF0TVJoOWJILVJwRGxWSENzbF9tY2VqT1RRb1Vxdko5SHdpV20tWUp0N2dOR2wyR1pUdW9FelFiT21UbkJITXFET0ZqTUVOMXBqdTVNdE1sbEI4OW55NlliUlh4ZG1BLlNmME9SNGJCa05CZmx2M3VLcUlhQXc.5yAy1dMOi_vJbIxv5zdor8jcFgW2Y9E_7Py-uQYZ3ZAILZaWf-k2igGL5ZPRFXZT5kTNTSdzNLjABDF3CN2viA'
        }
        self._loop = loop or asyncio.get_event_loop()
        self.user = self.session.query(User).filter(User.osf_id == user_osf_id).one() # todo: does passing in user directly break things?

    def stop(self):
        self._keep_running = False
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
        # if node/file is remote
        if isinstance(item, dict):
            if item['type'] == 'nodes':
                return item['id']
            elif item['type'] == 'files':
                #!!!!!!!!fixme: this is a cheatcode!!!! for here, we are using path+name+item_type for here only for identifying purposes
                # fixme: name doesnt work with modified names for folders.
                # fixme: doesn't work for when name/type/path is modified
                return str(hash(item['path'] + item['name'] + item['item_type']))
            else:
                raise ValueError(item['type'] +'is not handled')
        elif isinstance(item, Base):
            #todo: uncomment this assertion.
            # assert item.osf_id is not None
            return item.osf_id
        else:
            raise ValueError('What the fudge did you pass in?')


    # assumption: this method works.
    def make_local_remote_tuple_list(self, local_list, remote_list):
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
                if local_node.date_modified > self.remote_to_local_datetime(remote_node['date_modified']):
                    self.modify_remote_node(local_node, remote_node)
                else:
                    self.modify_local_node(local_node, remote_node)
        else:
            raise ValueError('in some weird state. figure it out.')

        #handle file_folders for node
        self.check_file_folder(local_node, remote_node,)

        #recursively handle node's children
        remote_children = self.get_all_paginated_members(remote_node['links']['children']['related'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)
        for local, remote in local_remote_nodes:
            self.check_node(local, remote, local_parent_node=local_node, remote_parent_node=remote_node)

    #todo: determine if we just want osfstorage or also other things
    def check_file_folder(self, local_node, remote_node):
        print('checking file_folder')
        # import pdb;pdb.set_trace()
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
            # remote_file_folder = self.create_remote_file_folder(local_file_folder, local_node, remote_parent_folder_or_node)
            pass
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
            # self.modify_file_folder_logic(local_file_folder, remote_file_folder, local_parent_file_folder, local_node)
            pass
        else:
            raise ValueError('in some weird state. figure it out.')

        assert local_file_folder is not None
        assert remote_file_folder is not None

        #recursively handle folder's children
        if local_file_folder.type == File.FOLDER:
            # import pdb;pdb.set_trace()
            remote_children = self.get_all_paginated_members(remote_file_folder['links']['related'])
            local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)
            for local, remote in local_remote_file_folders:
                self._check_file_folder(local, remote, local_parent_file_folder=local_file_folder, remote_parent_folder=remote_file_folder, local_node=local_node)

    def get_all_paginated_members(self, remote_url):
        remote_children = []
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

        #create local node folder on filesystem
        if not os.path.exists(new_node.path):
            os.makedirs(new_node.path)

        assert local_parent_node is None or (new_node in local_parent_node.components)
        return new_node


    def create_remote_node(self, local_node, remote_parent_node):
        print('create_remote_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_parent_node, dict)

        data={
            'title': local_node.title
        }
        resp = requests.put(remote_parent_node['links']['self'], data=data, headers=self.headers)
        if resp.ok:
            remote_node = resp.json()['data']
            local_node.osf_id = remote_node['id']
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
            user=self.user,
            parent=local_parent_folder,
            node=local_node)
        self.save(new_file_folder)

        #create local file/folder on actual system
        if not os.path.exists(new_file_folder.path):
            if type is File.FILE:
                resp = requests.get(remote_file_folder['links']['self'], headers=self.headers)
                with open(new_file_folder.path, 'wb') as fd:
                    for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                        fd.write(chunk)
            elif type is File.FOLDER:
                os.makedirs(new_file_folder.path)
            else:
                raise ValueError('file type is unknown')
        return new_file_folder

    def create_remote_file_folder(self, local_file_folder, local_node, remote_parent_folder_or_node):
        print('create_remote_file_folder')
        assert local_file_folder is not None
        assert isinstance(local_file_folder, File)
        assert local_node is not None
        assert isinstance(local_node, Node)
        assert remote_parent_folder_or_node is not None
        assert isinstance(remote_parent_folder_or_node, dict)

        params = {
                #fixme: path is probably incorrect. fix it.
                'path':local_file_folder.path.split('/osfstorage/')[1],# os.uncommon dir name (provider path, local_file_folder.path)
                'provider':local_file_folder.provider,
                'nid': local_node.osf_id
            }
        # print(params)
        params_string = '&'.join([k+'='+v for k,v in params.items()])
        file_url = remote_parent_folder_or_node['links']['self'].split('?')[0] + '?' + params_string
        # print(file_url)

        if local_file_folder.type == File.FOLDER:
            resp = requests.post(file_url, headers=self.headers )
        elif local_file_folder.type == File.FILE:
            files = {'file':open(local_file_folder.path)}
            resp = requests.put(file_url, headers=self.headers, files=files)

        if resp.ok:
            remote_file_folder = resp.json()['data']
            local_file_folder.osf_id = remote_file_folder['id']
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

        # modify local node on filesystem
        os.renames(old_path, local_node.path)

    def modify_remote_node(self, local_node, remote_node):
        print('modify_remote_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, dict)
        assert remote_node['type']=='nodes'
        assert remote_node['id'] == local_node.osf_id

        #todo: add other fields here.
        data = {
            'title': local_node.title
        }
        resp = requests.patch(remote_node['links']['self'],data=data, headers=self.headers)
        if not resp.ok:
            raise ValueError('remote node not modified:{}'.format(resp.content))

    def modify_local_file_folder(self, local_file_folder, remote_file_folder, local_parent_file_folder, local_node):
        print('modify_local_file_folder')
        assert isinstance(local_file_folder, File)
        assert isinstance(remote_file_folder, dict)
        assert remote_file_folder['type']=='files'
        assert remote_file_folder['id'] == local_file_folder.osf_id

        if local_file_folder.type == File.FOLDER:
            old_path = local_file_folder.path
            # update model
            local_file_folder.name = remote_file_folder['title']
            self.save(local_file_folder)

            # update local file system
            os.renames(old_path, local_file_folder.path)
        elif local_file_folder.type == File.FILE:
            #update model
            self.save(local_file_folder) # todo: does this actually update the local_file_folder timestamp???
            #update local file system
            resp = requests.get(remote_file_folder['links']['self'], headers=self.headers)
            with open(local_file_folder.path, 'wb') as fd:
                for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                    fd.write(chunk)

    # todo: handle other updates to file_folder
    def modify_file_folder_logic(self, local_file_folder, remote_file_folder):
        if local_file_folder.type is File.File:
                # todo: check if local version of file is different than online version
                # todo: HASH on remote server needed!!!!!!!
                if local_file_folder.date_modified > self.remote_to_local_datetime(remote_file_folder['date_modified']):
                    pass #todo: broken
                        # remote_file_folder = self.modify_remote_file_folder(local_file_folder, remote_file_folder, remote_parent_folder_or_node)
                elif local_file_folder.date_modified < self.remote_to_local_datetime(remote_file_folder['date_modified']):
                    self.modify_local_file_folder(local_file_folder, remote_file_folder)
        elif local_file_folder.type is File.FOLDER:
            if local_file_folder.name != remote_file_folder['name']:
                if local_file_folder.date_modified > self.remote_to_local_datetime(remote_file_folder['date_modified']):
                    pass #todo: broken
                    # remote_file_folder = self.modify_remote_file_folder(local_file_folder, remote_file_folder, remote_parent_folder_or_node)
                elif local_file_folder.date_modified < self.remote_to_local_datetime(remote_file_folder['date_modified']):
                    self.modify_local_file_folder(local_file_folder, remote_file_folder)
            else:
                raise ValueError('some weird type. fixit')

    def modify_remote_file_folder(self, local_file_folder, remote_file_folder, remote_parent_folder_or_node):
        print('modify_remote_file_folder. NOTE: this calls create_remote_file_folder and delete_file_folder')
        assert isinstance(local_file_folder, File)

        local_node = local_file_folder.node
        #handle modifying remote file folder by deleting then reuploading local file_folder
        self.delete_remote_file_folder(local_file_folder, remote_file_folder)
        new_remote_file_folder = self.create_remote_file_folder(local_file_folder, local_node, remote_parent_folder_or_node)

        return new_remote_file_folder



    #Delete

    def delete_local_node(self, local_node):
        print('delete_local_node')
        assert isinstance(local_node, Node)

        path = local_node.path

        #delete model
        self.session.delete(local_node)

        #delete from local
        shutil.rmtree(path)
        assert local_node is None

    #todo: delete_remote_node will have to handle making sure all children are deleted.
    def delete_remote_node(self, local_node, remote_node):
        print('delete_remote_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, dict)
        assert local_node.osf_id == remote_node['id']
        assert local_node.locally_deleted == True

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

        #delete model
        self.session.delete(local_file_folder)

        #delete from local
        shutil.rmtree(path)
        assert local_file_folder is None

    def delete_remote_file_folder(self, local_file_folder, remote_file_folder):
        assert local_file_folder is not None
        assert remote_file_folder is not None
        assert local_file_folder.osf_id == remote_file_folder['id']

        resp = requests.delete(remote_file_folder['links']['self'], headers=self.headers)
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


    def remote_to_local_datetime(self,remote_utc_time_string ):
        return iso8601.parse_date(remote_utc_time_string)

