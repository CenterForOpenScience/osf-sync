__author__ = 'himanshu'
import json
import os
import asyncio
import shutil
import concurrent
import pytz
import aiohttp

from osfoffline.database_manager.models import User, Node, File, Base
import osfoffline.alerts as alerts
import osfoffline.database_manager.db as db
from osfoffline.polling_osf_manager.api_url_builder import api_user_url, wb_file_revisions, wb_file_url, api_user_nodes,wb_move_url
from osfoffline.polling_osf_manager.osf_query import OSFQuery
from osfoffline.polling_osf_manager.remote_objects import RemoteObject, RemoteNode, RemoteFile, RemoteFolder,RemoteFileFolder

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

        self._loop = loop
        self.osf_query = OSFQuery(loop=self._loop, oauth_token=self.user.oauth_token)



    def stop(self):
        print('INSIDE polling.stop')
        self._keep_running = False
        try:
            self.session.close()
            print('just successfully closed the session')
        # except ProgrammingError:
        except:
            print('session NOT closed properly.')
        print('just tried to close the session')

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
    # It blocks check_osf from running.
    @asyncio.coroutine
    def get_remote_user(self, future):
        print("checking projects of user with id {}".format(self.user_osf_id))
        url = api_user_url(self.user_osf_id)
        while True:
            try:
                resp = yield from self.osf_query.make_request(url, get_json=True)
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
        if isinstance(item, RemoteObject):
            return item.id
        elif isinstance(item, Base):
            if item.osf_id:
                return item.osf_id
            else:
                assert item.locally_created
                return "FAKE{}FAKE".format(item.id)
        else:
            raise TypeError('What the fudge did you pass in?')

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
                if isinstance(sorted_combined_list[i], RemoteObject):  # remote
                    new_tuple = (sorted_combined_list[i + 1], sorted_combined_list[i])
                elif isinstance(sorted_combined_list[i], Base):  # local
                    new_tuple = (sorted_combined_list[i], sorted_combined_list[i + 1])
                else:
                    raise TypeError('what the fudge did you pass in')

                # add an extra 1 because both values should be added to tuple list
                i += 1
            elif isinstance(sorted_combined_list[i], RemoteObject):

                new_tuple = (None, sorted_combined_list[i])

            else:

                new_tuple = (sorted_combined_list[i], None)

            local_remote_tuple_list.append(new_tuple)
            i += 1

        for local, remote in local_remote_tuple_list:
            assert isinstance(local, Base) or local is None
            assert isinstance(remote, RemoteObject) or remote is None
            if isinstance(local, Base) and isinstance(remote, dict):
                assert local.osf_id == remote.id

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
            remote_top_level_nodes = yield from self.osf_query.get_top_level_nodes(all_remote_nodes_url)


            # get local top level nodes
            local_top_level_nodes = self.user.top_level_nodes

            local_remote_top_level_nodes = self.make_local_remote_tuple_list(local_top_level_nodes, remote_top_level_nodes)


            for local, remote in local_remote_top_level_nodes:
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
            if local_node.title != remote_node.name:
                yield from self.modify_local_node(local_node, remote_node)

        # handle file_folders for node
        yield from self.check_file_folder(local_node, remote_node)

        # recursively handle node's children
        remote_children = yield from self.osf_query.get_child_nodes(remote_node)
        local_remote_nodes = self.make_local_remote_tuple_list(local_node.child_nodes, remote_children)
        for local, remote in local_remote_nodes:
            yield from self.check_node(local, remote, local_parent_node=local_node)

    # todo: determine if we just want osfstorage or also other things
    @asyncio.coroutine
    def check_file_folder(self, local_node, remote_node):
        print('checking file_folder')
        remote_node_files = yield from self.osf_query.get_child_files(remote_node)
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
                remote_children = yield from self.osf_query.get_child_files(remote_file_folder)
                local_remote_file_folders = self.make_local_remote_tuple_list(local_file_folder.files, remote_children)
                for local, remote in local_remote_file_folders:
                    yield from self._check_file_folder(local,
                                            remote,
                                            local_parent_file_folder=local_file_folder,
                                            local_node=local_node)
            except ConnectionError:
                pass
                # if we are unable to get children, then we do not try to get and manipulate children



    # Create
    @asyncio.coroutine
    def create_local_node(self, remote_node, local_parent_node):
        print('create_local_node')
        assert isinstance(remote_node, RemoteNode)
        assert isinstance(local_parent_node, Node) or local_parent_node is None

        # create local node in db
        category = Node.PROJECT if remote_node.category == 'project' else Node.COMPONENT
        new_node = Node(
            title=remote_node.name,
            category=category,
            osf_id=remote_node.id,
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
        assert isinstance(remote_file_folder, RemoteFileFolder)
        assert isinstance(local_parent_folder, File) or local_parent_folder is None
        assert local_parent_folder is None or (local_parent_folder.type == File.FOLDER)
        assert isinstance(local_node, Node)

        # NOTE: develop is not letting me download files. dont know why.

        # create local file folder in db
        type = File.FILE if isinstance(remote_file_folder, RemoteFile) else File.FOLDER
        new_file_folder = File(
            name=remote_file_folder.name,
            type=type,
            osf_id=remote_file_folder.id,
            provider=remote_file_folder.provider,
            osf_path=remote_file_folder.id,
            user=self.user,
            parent=local_parent_folder,
            node=local_node
        )
        db.save(self.session, new_file_folder)

        # alert
        alerts.info(new_file_folder.name, alerts.DOWNLOAD)

        # create local file/folder on actual system
        if not os.path.exists(new_file_folder.path):
            if type == File.FILE:
                resp = yield from self.osf_query.make_request(remote_file_folder.download_url)
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

        if local_file_folder.type == File.FOLDER:
            remote_file_folder = yield from self.osf_query.upload_folder(local_file_folder)
        elif local_file_folder.type == File.FILE:
            try:
                remote_file_folder = yield from self.osf_query.upload_file(local_file_folder)
            except FileNotFoundError:
                print('file not created on remote server because does not exist locally. inside create_remote_file_folder')
                return

        local_file_folder.osf_id = remote_file_folder.id
        local_file_folder.osf_path = remote_file_folder.id
        local_file_folder.locally_created = False

        db.save(self.session,local_file_folder)

        return remote_file_folder

    # Modify
    @asyncio.coroutine
    def modify_local_node(self, local_node, remote_node):
        print('modify_local_node')
        assert isinstance(local_node, Node)
        assert isinstance(remote_node, RemoteNode)
        assert remote_node.id == local_node.osf_id

        old_path = local_node.path
        local_node.title = remote_node.name
        # todo: handle other fields such as category, hash, ...
        # local_node.category = remote_node.category

        db.save(self.session, local_node)

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
        assert isinstance(remote_file_folder,RemoteFileFolder)

        updated_remote_file_folder = None
        # this handles both files and folders being renamed
        if local_file_folder.name != remote_file_folder.name:
            if (yield from self.local_is_newer(local_file_folder, remote_file_folder)):
                updated_remote_file_folder = yield from self.rename_remote_file_folder(local_file_folder, remote_file_folder)
            else:
                yield from self.rename_local_file_folder(local_file_folder,  remote_file_folder)

        # if file size is different, then only do you  bother checking whether to upload or to download
        if local_file_folder.type == File.FILE and local_file_folder.size != remote_file_folder.size: # todo: local_file_folder.hash != remote_file_folder.size
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
        assert isinstance(remote_file_folder, RemoteFileFolder)
        assert remote_file_folder.id == local_file_folder.osf_path


        # alerts
        alerts.info(local_file_folder.name, alerts.MODIFYING)

        #handle renaming local file and local folder
        old_path = local_file_folder.path
        # update model
        local_file_folder.name = remote_file_folder.name
        db.save(self.session, local_file_folder)


        # update local file system
        try:
            os.renames(old_path, local_file_folder.path)
        except FileNotFoundError:
            print('folder not modified because doesnt exist. inside modify_local_file_folder (1)')

    @asyncio.coroutine
    def update_local_file(self, local_file, remote_file):
        assert isinstance(local_file, File)
        assert isinstance(remote_file, RemoteFile)
        assert remote_file.id == local_file.osf_path


        # todo: need the db file to be updated to show that its timestamp is in fact updated.
        # todo: can read this: http://docs.sqlalchemy.org/en/improve_toc/orm/events.html

        # update model
        # self.save(local_file_folder) # todo: this does NOT actually update the local_file_folder timestamp
        # update local file system
        try:
            resp = yield from self.osf_query.make_request(remote_file.download_url)
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
        assert isinstance(remote_file, RemoteFile)
        assert remote_file.id == local_file.osf_path

        alerts.info(local_file.name, alerts.MODIFYING)

        try:
            new_remote_file = yield self.osf_query.upload_file(local_file)
        except FileNotFoundError:
            print('file not created on remote server because does not exist locally. inside create_remote_file_folder')
            return remote_file



        return new_remote_file

    @asyncio.coroutine
    def rename_remote_file_folder(self, local_file_folder, remote_file_folder):
        print('rename_remote_file_folder.')
        assert isinstance(local_file_folder, File)
        assert isinstance(remote_file_folder, RemoteFileFolder)
        assert remote_file_folder.id == local_file_folder.osf_path
        assert local_file_folder.name != remote_file_folder['name']

        # alerts
        alerts.info(local_file_folder.name, alerts.MODIFYING)

        if local_file_folder.type == File.FILE:
            new_remote_file_folder = yield from self.osf_query.rename_remote_file(local_file_folder, remote_file_folder)
        elif local_file_folder.type == File.FOLDER:
            new_remote_file_folder = yield from self.osf_query.rename_remote_folder(local_file_folder, remote_file_folder)

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

        if local_file_folder.type == File.FILE:
            yield from self.osf_query.delete_remote_file(remote_file_folder)
        elif local_file_folder.type == File.FOLDER:
            yield from self.osf_query.delete_remote_folder(remote_file_folder)

        local_file_folder.deleted = False
        self.session.delete(local_file_folder)
        db.save(self.session)



    # todo: determine proper logic for when to update local/remote. (specifically for files based on datetime for now.)
    @asyncio.coroutine
    def _get_local_remote_times(self, local, remote):
        assert local
        assert remote
        assert isinstance(local, Base)
        assert isinstance(remote, RemoteObject)

        local_time = local.date_modified.replace(tzinfo=pytz.utc)
        if isinstance(remote, RemoteFileFolder):
            remote_time = yield from remote.last_modified(local.node.id, self.osf_query)
        else:
            remote_time = remote.last_modified

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
            if isinstance(remote, RemoteFile):
                return local.size > remote.size
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
            if isinstance(remote, RemoteFile):
                return local.size < remote.size
            else:
                return False

        return local_time < remote_time

def console_log(variable_name, variable_value):
    print("DEBUG: {}: {}".format(variable_name, variable_value))