from osfoffline.settings import API_BASE, WB_BASE
from furl import furl

#from osfoffline
from osfoffline.polling_osf_manager.api_url_builder import api_file_children, api_user_nodes,api_user_url,wb_file_url,wb_move_url,wb_file_revisions

# ONLY FOR TESTING
def api_node_self(node_id):
    # http://localhost:8000/v2/nodes/dz5mg/
    base = furl(API_BASE)
    base.path.segments.extend(['nodes',str(node_id)])
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


def api_create_node():
    base = furl(API_BASE)
    base.path.segments.extend(['v2','nodes'])
    return base.url

