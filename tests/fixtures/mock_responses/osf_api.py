import json

from osfoffline.polling_osf_manager.api_url_builder import api_user_nodes
from tests.fixtures.mock_responses.common import Session
from furl import furl
from decorator import decorator
from tests.fixtures.mock_responses.models import User, Node, File
session = Session()

def save(item=None):
    if item is not None:
        session.add(item)
    session.commit()

# create functions
def create_new_user():
    user = User()
    save(user)
    return user

def create_new_top_level_node(user):
    node = Node(user=user)
    save(user)
    save(node)
    return node

def create_new_node(super_node):
    node = Node(user=super_node.user)
    super_node.nodes.append(node)
    save(super_node)
    save(node)
    return node

def create_provider_folder(node):
    folder = File(type=File.FOLDER, node=node, user=node.user)
    save(folder)
    save(node)
    return folder

def create_new_folder(folder):
    new_folder = File(type=File.FOLDER, node=folder.node, user=folder.user, parent=folder)
    save(folder)
    save(new_folder)
    return new_folder

def create_new_file(folder):

    new_file = File(type=File.FILE, node=folder.node, user=folder.user, parent=folder)
    save(new_file)
    save(folder)
    return new_file


# helpers
@decorator
def must_be_logged_in(func, *args, **kwargs):
    try:

        id = user_id_from_request(args[0])
        session.query(User).filter(User.id==id).one()
        return func(*args, **kwargs)
    except:
        return (404, args[0].headers, 'something wrong with must_be_logged_in func')


def user_id_from_request(request):
    bearer_plus_id = request.headers.get('Authorization')
    id = bearer_plus_id.split(' ')[1]
    return id


@must_be_logged_in
def get_user(request, uri, headers):
    try:

        id = furl(uri).path.segments[2]
        user = session.query(User).filter(User.id ==id).one()
        resp = json.dumps(
            {
                'data': user.as_dict()
            }
        )
        return 200, headers, resp
    except:
        return 400, headers, 'ERROR in get_user.'

@must_be_logged_in
def get_user_nodes(request, uri, headers):
    try:
        user_id = furl(uri).path.segments[2]
        user = session.query(User).filter(User.id ==user_id).one()
        nodes = user.nodes
        resp = [node.as_dict() for node in nodes]
        resp = json.dumps({
            'data':resp
        })
        return (200, headers, resp)
    except:
        return (400, headers, 'cant get user nodes')



@must_be_logged_in
def get_providers_for_node(request, uri, headers):
    try:

        nid = furl(uri).path.segments[2]
        node = session.query(Node).filter(Node.id == nid).one()

        resp = [provider.as_dict() for provider in node.providers]
        resp = json.dumps({
            'data':resp
        })
        return (200, headers, resp)
    except:
        return (400, headers, 'cant get providers for node')

@must_be_logged_in
def get_children_for_folder(request, uri, headers):
    try:

        folder_path = furl(uri).args['path']

        nid = furl(uri).path.segments[2]

        for file_folder in session.query(File):
            if not file_folder.is_file:
                if file_folder.node.id == int(nid) and file_folder.path == folder_path:
                    resp = [child.as_dict() for child in file_folder.files]
                    resp = json.dumps({
                        'data':resp
                    })
                    return (200, headers, resp)
    except:
        return (400, headers, 'cant get providers for node')

@must_be_logged_in
def create_folder(request, uri, headers):
    folder_path = furl(uri).args['path']
    # folder_name = folder_path.split('/')[1]
    # provider_name = furl(uri).args['path']
    nid = furl(uri).args['nid']
    provider = session.query(File).filter(File.parent == None and File.node_id==nid).one()
    new_folder = create_new_folder(provider)
    resp = json.dumps({
        'data':new_folder.as_dict()
    })
    return (200, headers, resp)

@must_be_logged_in
def create_file(request, uri, headers):
    folder_path = furl(uri).args['path']
    # folder_name = folder_path.split('/')[1]
    # provider_name = furl(uri).args['path']
    nid = furl(uri).args['nid']
    provider = session.query(File).filter(File.parent == None and File.node_id==nid).one()
    new_file = create_new_file(provider)
    resp = json.dumps({
        'data':new_file.as_dict()
    })
    return (200, headers, resp)

