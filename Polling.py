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
from models import User, Node, File, create_engine, sessionmaker, get_session
from sqlalchemy.orm import scoped_session
from sqlalchemy.pool import SingletonThreadPool
import iso8601
import requests



class Poll(Thread):
    def __init__(self, db_url, user_osf_id, session):
        super().__init__()
        self._keep_running = True
        self.db_url = db_url
        self.user_osf_id = user_osf_id
        self._loop = None
        db_file_path = os.path.join(self.db_url, 'osf.db')
        url = 'sqlite:///{}'.format(db_file_path)
        #todo: figure out if this is safe or not. If not, how to make it safe?????
        # engine = create_engine(url, echo=False, connect_args={'check_same_thread':False})
        engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
        session_factory = sessionmaker(bind=engine)
        global Session
        Session = scoped_session(session_factory)
        self.session = Session()

    def stop(self):
        self._keep_running = False
        # self._loop.close()

    def run(self):

        self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.


        asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        remote_user = self.get_remote_user()



        self._loop.run_until_complete(self.check_osf(remote_user,self.db_url,5))



    def get_remote_user(self):
        print(self.user_osf_id)
        return requests.get('https://staging2.osf.io:443/api/v2/users/{}/'.format(self.user_osf_id)).json()['data']


    def get_id(self,item):
        """

        :param item: node or fileF
        :return: guid of item
        """

        # if node/file is remote
        if isinstance(item, dict):
            if item['type'] == 'nodes':
                return item['id']
            else: #assumption: item['type'] == 'files'
                #!!!!!!!!fixme: this is a cheatcode!!!! for here, we are using path+name+item_type for here only for identifying purposes
                # fixme: name doesnt work with modified names for folders.
                return str(hash(item['path']+item['name']+item['item_type']))
        else: # node/file is local


            return item.osf_id


    #assumption: this method works.
    def make_local_remote_tuple_list(self, local_list, remote_list):
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
                else:#assumption: sorted_combined_list[i] is a local object
                    new_tuple = (sorted_combined_list[i],sorted_combined_list[i+1])
                i += 1 #add an extra 1 because both values should be added to tuple list
            elif isinstance(sorted_combined_list[i], dict):
                new_tuple = (None,sorted_combined_list[i])
            else:
                new_tuple = (sorted_combined_list[i], None)
            local_remote_tuple_list.append( new_tuple )
            i += 1
        return local_remote_tuple_list



    @asyncio.coroutine
    def check_osf(self,remote_user,db_url, recheck_time=None):

        # Session.configure(bind=engine)

        print('error here?')
        remote_user_id = remote_user['id']
        print('error here??')
        self.user = self.session.query(User).filter(User.osf_id == remote_user_id).first()
        print('error here???')
        projects_for_user_url = 'https://staging2.osf.io:443/api/v2/users/{}/nodes/?filter[category]=project'.format(remote_user_id)

        while self._keep_running:
            #get remote projects
            resp = requests.get(projects_for_user_url)
            remote_projects = resp.json()['data']
            # remote_project_guids = [remote_project['guid'] for remote_project in remote_projects ]

            #get local projects
            local_projects = self.user.projects
            # local_project_guids = [local_project.guid for local_project in local_projects ]


            local_remote_projects = self.make_local_remote_tuple_list(local_projects, remote_projects)

            for local, remote in local_remote_projects:
                # optimization: could check date modified of top level
                # and if not modified then don't worry about children
                self.check_node(local, remote, parent=None)


            print('---------SHOULD HAVE ALL OSF FILES---------')

            if recheck_time:
                #todo: figure out how we can prematuraly stop the sleep when user ends the application while sleeping
                print('SLEEPING FOR {} seconds...'.format(recheck_time))
                yield from asyncio.sleep(recheck_time)



    def check_node(self,local_node, remote_node, parent):
        """
        Responsible for checking whether local node values are same as remote node.
        Values to be checked include: files and folders, name, metadata, child nodes
        """
        print('checking node')

        #get local or remote, whichever is None
        #todo: add date_modified checks to this
        if local_node is None:
            local_node = self.download_node(remote_node, parent)
        elif remote_node is None:
            remote_node = self.upload_node(local_node, parent)
        #handle file_folders for node
        self.check_file_folder(local_node, remote_node)

        #handle updates to current node
        if local_node.title != remote_node['title']:
            if local_node.date_modified > self.remote_to_local_datetime(remote_node['date_modified']):
                self.modify_remote_node(local_node, remote_node)
            else:
                self.modify_local_node(local_node, remote_node)


        #recursively handle node's children
        remote_children = []
        resp = requests.get(self.fix_request_issue(remote_node['links']['children']['related'])).json()

        remote_children.extend(resp['data'])
        while resp['links']['next'] != None:
            resp = requests.get(self.fix_request_issue(resp['links']['next'])).json()
            remote_children.extend(resp['data'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)

        for local, remote in local_remote_nodes:
            self.check_node(local, remote, parent=local_node)



    def download_node(self, remote_node, parent):
        print('downloading node')
        category = Node.PROJECT if remote_node['category']=='project' else Node.COMPONENT
        if parent:
            new_node_path = os.path.join(parent.path, remote_node['title'])
        else:
            new_node_path = os.path.join(self.user.osf_path,remote_node['title'])
        new_node = Node(title=remote_node['title'], category=category, osf_id=remote_node['id'], path=new_node_path, user=self.user)
        self.session.add(new_node)
        self.save()

        #also create local folder for node
        if not os.path.exists(new_node_path):
            os.makedirs(new_node_path)

        return new_node

    def modify_remote_node(self, local_node, remote_node):
        print('modifying remote node!')
        pass

    def modify_local_node(self, local_node, remote_node):
        print('modifying local node')

        old_path = local_node.path



        local_node.title = remote_node['title']
        local_node.path = os.path.join(os.path.basename(local_node.path), remote_node['title'])
        # todo: handle other fields such as category, hash, ...
        self.save()

        #if a folder changes, the paths of ALL children also change
        self.update_childrens_path(local_node)

        # save
        self.session.add(local_node)
        self.save()


        #also actually modify local node
        os.renames(old_path, local_node.path)

    def update_childrens_path(self, local_node):
        for child in local_node.components:
            child.path = os.path.join(local_node.path,child.title)
            self.update_childrens_path(child)



    def upload_node(self, local_node, parent):
        # requests.put('https://staging2.osf.io:443/api/v2/nodes/{}/'.format())
        print('uploading node!')
        return None


    def check_file_folder(self, local_node, remote_node):

        print('checking file_folder')
        #todo: determine if we just want osfstorage or also other things
        resp = requests.get(self.fix_request_issue(remote_node['links']['files']['related']))
        remote_node_files = resp.json()['data']
        print('DEBUG:local_node.files:{}'.format(local_node.files))
        print('DEBUG:remote_node_files:{}'.format(remote_node_files))
        local_remote_files = self.make_local_remote_tuple_list(local_node.files, remote_node_files)

        for local, remote in local_remote_files:
            self._check_file_folder(local, remote, parent=local_node)


    def _check_file_folder(self,local_file_folder,remote_file_folder, parent):
        print('checking file_folder internal')

        if local_file_folder is None:
            local_file_folder = self.create_local_file_folder(remote_file_folder, parent)
        elif remote_file_folder is None:
            remote_file_folder = self.create_remote_file_folder(local_file_folder, parent)


        #todo: handle file/folder name, content changes.

        if local_file_folder.type is File.FILE:
            #todo: check if local version of file is different than online version
            pass
        else: #assumption: local_file_folder.type is File.Folder
            #recursively handle folder's children
            remote_children = []

            try:
                resp = requests.get(self.fix_request_issue(remote_file_folder['links']['related']))
                remote_children.extend(resp.json()['data'])
                while resp.json()['links']['next'] != None:#fixme: don't know actual response. figure it out.
                    resp = requests.get(self.fix_request_issueresp['links']['next']).json()
                    remote_children.extend(resp['data'])

                local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)
                for local, remote in local_remote_file_folders:
                    self._check_file_folder(local, remote, parent=local_file_folder)
            except:

                print('couldnt get subfolder and subfiles. no permission. todo: make seperate helper functions to get these values.')



    def create_local_file_folder(self, remote_file_folder, parent):
        import threading; print('------------------------inside create_local_file_folder---{}----'.format(threading.current_thread()))
        type = File.FILE if remote_file_folder['item_type']=='file' else File.FOLDER
        # handles case where parent is node and when parent is folder
        new_file_folder_path = os.path.join(parent.path, remote_file_folder['name'])
        parent_folder = parent if isinstance(parent, File) else None
        #The json response contains path. assumption: this path variable is uniquily identifying to a folder/file

        #note the hack: osf_id = self.get_id(remote) is a made up osf_id
        new_file_folder = File(name=remote_file_folder['name'], type=type, osf_id=self.get_id(remote_file_folder), path=new_file_folder_path, user=self.user, parent=parent_folder)
        self.session.add(new_file_folder)
        self.save()
        print('DEBUG:new_file_folder.osf_id:{}'.format(new_file_folder.osf_id))

        #also create local file/folder
        if not os.path.exists(new_file_folder_path):
            if type is File.FILE:
                resp = requests.get(self.fix_request_issueremote_file_folder['links']['self'])
                with open(new_file_folder_path, 'wb') as fd:
                    for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                        fd.write(chunk)
            else:#assumption: type is File.Folder
                    os.makedirs(new_file_folder_path)

        return new_file_folder

    def create_remote_file_folder(self, local_file_folder, parent):
        print('uploaded file/folder to server!')
        return None

    def save(self):
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise


    def remote_to_local_datetime(self,remote_utc_time_string ):
        return iso8601.parse_date(remote_utc_time_string)

    def fix_request_issue(self, url):
        if '/api/api/' in url:
            i_api = url.index('/api/api/')
            return url[:i_api]+url[i_api+4:]
        return url
