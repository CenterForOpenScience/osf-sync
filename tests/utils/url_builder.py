from osfoffline.settings import API_BASE
from furl import furl

#from osfoffline
from osfoffline.polling_osf_manager.api_url_builder import (
    api_file_children,
    api_user_nodes,
    api_user_url,
    wb_file_url,
    wb_move_url,
    wb_file_revisions)

# ONLY FOR TESTING
def api_node_self(node_id):
    # http://localhost:8000/v2/nodes/dz5mg/
    base = furl(API_BASE)
    base.path.segments.extend(['v2','nodes',str(node_id)])
    return base.url


# ONLY FOR TESTING
def api_node_children(node_id):
    # http://localhost:8000/v2/nodes/dz5mg/children/
    base = furl(API_BASE)
    base.path.segments.extend(['v2','nodes',str(node_id), 'children'])
    return base.url

# ONLY FOR TESTING
def api_node_files(node_id):
    # http://localhost:8000/v2/nodes/dz5mg/files/
    base = furl(API_BASE)
    base.path.segments.extend(['v2','nodes',str(node_id), 'files'])
    return base.url

#ONLY FOR TESTING
def api_file_self(path, nid, provider):
    return wb_file_url(path=path, nid=nid, provider=provider)


def api_create_node(parent_node_id=None):
    base = furl(API_BASE)
    if parent_node_id:
        if 'localhost' in API_BASE:
            base.port = '5000'
        base.path.segments = [str(parent_node_id), 'newnode']
    else:
        base.path.segments.extend(['v2','nodes'])
    return base.url


def api_next_child_nodes(parent_node_id):
    # http://localhost:8000/v2/users/szyrp/nodes/?page=2
    base = furl(API_BASE)
    base.path.segments.extend(['v2','users',str(parent_node_id), 'nodes'])
    return base.url


def api_create_user_url():
    base = furl(API_BASE)
    base.path.segments.extend(['v2','users'])
    return base.url