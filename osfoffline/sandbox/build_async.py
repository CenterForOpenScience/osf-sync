import asyncio
import os

import iso8601
from watchdog.observers import Observer
from sqlalchemy.pool import SingletonThreadPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import requests

from osfoffline.models import User, Node, File, get_session, Base


EVENT_TYPE_MOVED = 'moved'
EVENT_TYPE_DELETED = 'deleted'
EVENT_TYPE_CREATED = 'created'
EVENT_TYPE_MODIFIED = 'modified'

class AIOEventHandler(object):
    """An asyncio-compatible event handler."""

    def __init__(self, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self.num_user = 0
        print('inside aioenventhandler loop is {}'.format(self._loop))



    @asyncio.coroutine
    def on_any_event(self, event):
        # print(event)
        session = get_session()
        for user in session.query(User):
            print(user.fullname)
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_moved(self, event):
        print('moved')
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_created(self, event):
        print('created')
        session = get_session()
        user = User(fullname='user{}'.format(self.num_user))
        session.add(user)
        session.commit()
        self.num_user += 1
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_deleted(self, event):
        print('delted')
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_modified(self, event):
        print('modified')
        yield from asyncio.sleep(1)

    def dispatch(self, event):
        _method_map = {
            EVENT_TYPE_MODIFIED: self.on_modified,
            EVENT_TYPE_MOVED: self.on_moved,
            EVENT_TYPE_CREATED: self.on_created,
            EVENT_TYPE_DELETED: self.on_deleted,
        }
        handlers = [self.on_any_event, _method_map[event.event_type]]
        for handler in handlers:

            self._loop.call_soon_threadsafe(
                asyncio.async,
                handler(event)
            )


class AIOWatchdog(object):

    def __init__(self, path='.', recursive=True, event_handler=None):
        self._observer = Observer()
        evh = event_handler or AIOEventHandler()
        self._observer.schedule(evh, path, recursive)

    def start(self):
        print('starting watchdog')
        self._observer.start()

    def stop(self):
        self._observer.stop()
        self._observer.join()
        print('stopped watchdog')

# @asyncio.coroutine
# def run_watchdog():
#     myeventhandler = AIOEventHandler(loop=loop)
#     watch = AIOWatchdog('/home/himanshu/OSF-Offline/sandbox/dumbdir/', event_handler=)
#     watch.start()
#     for _ in range(20):
#         yield from asyncio.sleep(1)
#     watch.stop()

Session = None
def make_session():
    url = 'sqlite:///{}'.format('/home/himanshu/OSF-Offline/sandbox/concurrent.db')
    engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
    session_factory = sessionmaker(bind=engine)
    global Session
    Session = scoped_session(session_factory)
    Base.metadata.create_all(engine)

def get_session():
    return Session()


def poll():
    print('polling the api')
    session = get_session()
    resp = requests.get('http://www.google.com')
    user = User(fullname=resp.content[:4])
    session.add(user)
    session.commit()
    print('----poll start--------')
    for user in session.query(User):
        print(user.fullname)
    print('----poll end--------')
    asyncio.get_event_loop().call_later(3, poll)




    def get_remote_user(self):
        print(self.user_osf_id)
        resp = requests.get('https://staging2.osf.io:443/api/v2/users/{}/'.format(self.user_osf_id), headers=self.headers)


        if resp.ok:
            return resp.json()['data']
        raise ValueError


    def get_id(self, item):
        """

        :param item: node or fileF
        :return: guid of item
        """

        # if node/file is remote
        if isinstance(item, dict):
            if item['type'] == 'nodes':
                return item['id']
            elif item['type'] == 'files':
                #!!!!!!!!fixme: this is a cheatcode!!!! for here, we are using path+name+item_type for here only for identifying purposes
                # fixme: name doesnt work with modified names for folders.
                #fixme: doesn't work for when name/type/path is modified
                return str(hash(item['path'] + item['name'] + item['item_type']))
            else:
                raise ValueError(item['type'] +'is not handled')
        elif isinstance(item, Base):
            return item.osf_id
        else:
            raise ValueError('What the fudge did you pass in?')


    # assumption: this method works.
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



    @asyncio.coroutine
    def check_osf(self,remote_user,db_url, recheck_time=None):

        # Session.configure(bind=engine)

        print('error here?')
        remote_user_id = remote_user['id']
        print('error here??')
        self.user = self.session.query(User).filter(User.osf_id == remote_user_id).first()
        print('error here???')
        projects_for_user_url = 'https://staging2.osf.io:443/api/v2/users/{}/nodes/'.format(remote_user_id)

        while self._keep_running:
            #get remote projects
            resp = requests.get(projects_for_user_url, headers=self.headers)
            remote_projects = resp.json()['data']

            #todo: figure out how to actually get top level nodes. FOR NOW, I am just filtering by category = projects in response.
            temp = []
            for remote in remote_projects:
                if remote['category'] == 'project':
                    temp.append(remote)
            remote_projects = temp

            #get local projects
            local_projects = self.user.projects

            local_remote_projects = self.make_local_remote_tuple_list(local_projects, remote_projects)
            print("DEBUG: check_osf: local_remote_projects:{}".format(local_remote_projects))

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
        assert (local_node is not None) or (remote_node is not None) # both shouldnt be none.
        # todo: add date_modified checks to this

        # NOTE: must delete all lower level nodes before can delete top level node.
        if local_node is not None and local_node.deleted:
            self.delete_remote_node(local_node, remote_node)
            assert local_node is None #not sure if local node is reloaded in this case. assert might fail.
        elif remote_node is None:
            assert local_node is not None
            remote_node = self.upload_node(local_node, parent)
        elif local_node is None:
            local_node = self.download_node(remote_node, parent)
        else:


            #handle updates to current node
            if local_node.title != remote_node['title']:
                if local_node.date_modified > self.remote_to_local_datetime(remote_node['date_modified']):
                    self.modify_remote_node(local_node, remote_node)
                else:
                    self.modify_local_node(local_node, remote_node)

        #handle file_folders for node
        self.check_file_folder(local_node, remote_node)


        #recursively handle node's children
        remote_children = []
        resp = requests.get(self.fix_request_issue(remote_node['links']['children']['related']), headers=self.headers).json()

        remote_children.extend(resp['data'])
        while resp['links']['next'] != None:
            resp = requests.get(self.fix_request_issue(resp['links']['next']), headers=self.headers).json()
            remote_children.extend(resp['data'])
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.components, remote_children)

        for local, remote in local_remote_nodes:
            self.check_node(local, remote, parent=local_node)

    def delete_remote_node(self,local_node, remote_node):
        assert local_node.deleted

        #delete children
        for child in local_node.components:
            self.delete_remote_node(child)

        resp = requests.delete(remote_node['links']['self'], headers=self.headers)
        if resp.ok:#todo: what is this ok field?
            self.session.delete(local_node)




    def download_node(self, remote_node, parent):
        print('downloading node')
        category = Node.PROJECT if remote_node['category']=='project' else Node.COMPONENT

        new_node = Node(title=remote_node['title'], category=category, osf_id=remote_node['id'], user=self.user, parent=parent)
        self.save(new_node)

        #also create local folder for node
        if not os.path.exists(new_node.path):
            os.makedirs(new_node.path)

        return new_node

    def modify_remote_node(self, local_node, remote_node):
        print('modifying remote node!')
        #add other fields here.
        data = {
            'title': local_node.title
        }
        requests.patch(remote_node['links']['self'],data=data, headers=self.headers )


    def modify_local_node(self, local_node, remote_node):
        print('modifying local node')

        old_path = local_node.path



        local_node.title = remote_node['title']
        # todo: handle other fields such as category, hash, ...




        # save
        self.save(local_node)

        # also actually modify local node
        os.renames(old_path, local_node.path)




    def upload_node(self, local_node, parent):
        # requests.put('https://staging2.osf.io:443/api/v2/nodes/{}/'.format())
        print('uploading node!')
        data={
            'title': local_node.title
        }
        resp = requests.put(parent['links']['self'], data=data, headers=self.headers)
        if resp.ok:
            remote_node = resp.json()['data']
            local_node.created = False
            local_node.osf_id = remote_node['id']
            self.save(local_node)
            return remote_node
        return None


    def check_file_folder(self, local_node, remote_node):

        print('checking file_folder')
        #todo: determine if we just want osfstorage or also other things
        resp = requests.get(self.fix_request_issue(remote_node['links']['files']['related']), headers=self.headers)

        #todo: top level more than 10 files not handled yet

        remote_node_files = resp.json()['data']
        local_remote_files = self.make_local_remote_tuple_list(local_node.files, remote_node_files)

        for local, remote in local_remote_files:
            self._check_file_folder(local, remote, local_parent=None,node=local_node)

    #todo: split this giant function up.
    def _check_file_folder(self,local_file_folder,remote_file_folder, local_parent, node):
        print('checking file_folder internal')

        if local_file_folder is not None and local_file_folder.deleted:
            self.delete_remote_file_folder(local_file_folder, remote_file_folder)
        elif remote_file_folder is None:
            assert local_file_folder is not None
            self.create_remote_file_folder(local_file_folder, local_parent)
        elif local_file_folder is None:
            assert remote_file_folder is not None
            self.create_local_file_folder(remote_file_folder, local_parent, node=node)
        # if local_file_folder is None:
        #     local_file_folder = self.create_local_file_folder(remote_file_folder, parent)
        # elif remote_file_folder is None:
        #     remote_file_folder = self.create_remote_file_folder(local_file_folder, parent)


        #todo: handle file/folder name, content changes.

        if local_file_folder.type is File.FILE:

            #todo: check if local version of file is different than online version
            #todo: HASH on remote server needed!!!!!!!
            if local_file_folder.date_modified > self.remote_to_local_datetime(remote_file_folder['date_modified']):
                #modify remote file folder
                print('re - uploading remote file')
                remote_file_folder = self.create_remote_file_folder(local_file_folder, local_parent)

            elif local_file_folder.date_modified < self.remote_to_local_datetime(remote_file_folder['date_modified']):

                # update model to reflect new date_modified and HASH
                local_file_folder.date_modified = self.remote_to_local_datetime(remote_file_folder['date_modified'])
                self.save(local_file_folder)

                # redownload file
                resp = requests.get(self.fix_request_issue(remote_file_folder['links']['self']), headers=self.headers)
                with open(local_file_folder.path, 'wb') as fd:
                    for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                        fd.write(chunk)
        else: #assumption: local_file_folder.type is File.Folder

            if local_file_folder.name != remote_file_folder['name']:
                if local_file_folder.date_modified > self.remote_to_local_datetime(remote_file_folder['date_modified']):
                    self.modify_local_folder(local_file_folder, remote_file_folder)
                else:
                    self.modify_remote_folder(local_file_folder, local_parent)


            #recursively handle folder's children
            remote_children = []

            try:
                #todo: make helper function to get all children at once.
                resp = requests.get(self.fix_request_issue(remote_file_folder['links']['related']), headers=self.headers)
                remote_children.extend(resp.json()['data'])
                while resp.json()['links']['next'] != None:#fixme: don't know actual response. figure it out.
                    resp = requests.get(self.fix_request_issue(resp['links']['next']), headers=self.headers).json()
                    remote_children.extend(resp['data'])

                local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)

                for local, remote in local_remote_file_folders:
                    self._check_file_folder(local, remote, local_parent=local_file_folder, node=node)
            except:
                print('couldnt get subfolder and subfiles. no permission. todo: make seperate helper functions to get these values. ???what are <these> referring to?...')

    def modify_remote_folder(self, local_file_folder, parent):
        print('modifying remote file folder')
        assert local_file_folder is not None
        # assert remote_file_folder is not None
        # assert remote_file_folder['']
        # assert local_file_folder.name != remote_file_folder['name']

        # data = {
        #     'name':local_file_folder.name
        # }
        # requests.patch(remote_file_folder['links']['self'],data=data, header=self.headers)
        self.create_remote_file_folder(local_file_folder, parent)

    def modify_local_folder(self, local_folder, remote_folder):
        print('modifying local folder')

        old_path = local_folder.path



        local_folder.title = remote_folder['title']
        # todo: handle other fields such as category, hash, ...
        self.save()


        # save
        self.session.add(local_folder)
        self.save()


        #also actually modify local folder
        os.renames(old_path, local_folder.path)


    def create_local_file_folder(self, remote_file_folder, parent, node):
        assert remote_file_folder is not None
        assert isinstance(parent, File) or parent is None
        assert isinstance(node, Node)
        type = File.FILE if remote_file_folder['item_type']=='file' else File.FOLDER
        # handles case where parent is node and when parent is folder

        parent_folder = parent if isinstance(parent, File) else None
        #The json response contains path. assumption: this path variable is uniquily identifying to a folder/file


        #note the hack: osf_id = self.get_id(remote) is a made up osf_id
        new_file_folder = File(name=remote_file_folder['name'], type=type, osf_id=self.get_id(remote_file_folder), user=self.user, parent=parent_folder, node=node)
        self.session.add(new_file_folder)
        self.save()
        print('DEBUG:new_file_folder.osf_id:{}'.format(new_file_folder.osf_id))

        #also create local file/folder
        if not os.path.exists(new_file_folder.path):
            if type is File.FILE:
                resp = requests.get(self.fix_request_issue(remote_file_folder['links']['self']), header=self.headers)
                with open(new_file_folder.path, 'wb') as fd:
                    for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
                        fd.write(chunk)
            else:#assumption: type is File.Folder
                    os.makedirs(new_file_folder.path)

        return new_file_folder

    def modify_remote_file_folder(self, local_file_folder, parent):
        assert local_file_folder is not None
        assert parent is not None
        assert local_file_folder in parent.files
        print('re uploading file/folder to server!')
        return self.create_remote_file_folder(local_file_folder, parent)


    def create_remote_file_folder(self, local_file_folder, parent):
        assert local_file_folder is not None
        assert parent is not None
        assert local_file_folder in parent.components

        print('uploaded file/folder to server!')
        if local_file_folder.type == File.FOLDER:
            print('DEBUG:create_remote_file_folder:local_file_folder.path.split(/osfstorage/)[1]:{}',local_file_folder.path.split('/osfstorage/')[1])
            params = {
            'path':local_file_folder.path.split('/osfstorage/')[1],# os.uncommon dir name (provider path, local_file_folder.path)
            'provider':'osfstorage',
             'nid': parent.node_id#'8c6mu'# node.osf_id
            }
            params_string = '&'.join([k+'='+v for k,v in params.items()])
            file_url = parent['links']['self'].split('?')[0] + '?' + params_string

            resp = requests.post(file_url, headers=self.headers )
            # resp = requests.put(parent['links']['self'], data=data, header=self.headers)
            if resp.ok:
                remote_file_folder = resp.json()['data']
                local_file_folder.osf_id = remote_file_folder['id']
                self.save(local_file_folder)
                return remote_file_folder
        elif local_file_folder.type == File.FILE:
            print('DEBUG:create_remote_file_folder:local_file_folder.path.split(/osfstorage/)[1]:{}',local_file_folder.path.split('/osfstorage/')[1])
            params = {
            'path':local_file_folder.path.split('/osfstorage/')[1],# os.uncommon dir name (provider path, local_file_folder.path)
            'provider':'osfstorage',
             'nid': parent.node_id#'8c6mu'# node.osf_id
            }
            params_string = '&'.join([k+'='+v for k,v in params.items()])
            file_url = parent['links']['self'].split('?')[0] + '?' + params_string

            files = {'file':open(local_file_folder.path)}
            resp = requests.put(file_url, headers=self.headers, files=files)
            if resp.ok:
                remote_file_folder = resp.json()['data']
                local_file_folder.osf_id = remote_file_folder['id']
                self.save(local_file_folder)
                return remote_file_folder
        return None

    def delete_remote_file_folder(self, local_file_folder, remote_file_folder):
        assert local_file_folder is not None
        assert remote_file_folder is not None
        assert local_file_folder.osf_id == remote_file_folder['id']

        resp = requests.delete(remote_file_folder['links']['self'], headers=self.headers)
        if resp.ok:
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


    def remote_to_local_datetime(self,remote_utc_time_string ):
        return iso8601.parse_date(remote_utc_time_string)

    def fix_request_issue(self, url):
        if '/api/api/' in url:
            i_api = url.index('/api/api/')
            return url[:i_api]+url[i_api+4:]
        return url

if __name__=="__main__":
    # logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    make_session()
    session = get_session()
    # print(loop)
    OSFFileWatcher = AIOEventHandler(loop=loop)
    # loop.set_debug(True)
    # run_watchdog()
    watchdog = AIOWatchdog(path='/home/himanshu/OSF-Offline/sandbox/dumbdir/', event_handler=OSFFileWatcher)
    watchdog.start()
    loop.call_later(3, poll)
    # loop.run_forever()
    loop.run_forever()
    # print('haha, this printed.')


