from osfoffline.settings import API_BASE, WB_BASE
from furl import furl


def api_user_url(user_id):
    # http://localhost:8000/v2/users/5bqt9/
    base = furl(API_BASE)
    base.path.segments = ['v2','users',str(user_id),'']
    return base.url


def api_user_nodes(user_id):
    # http://localhost:8000/v2/users/5bqt9/nodes/
    base = furl(API_BASE)
    base.path.segments = ['v2','users', str(user_id), 'nodes', '']
    return base.url

def api_file_children(node_id, path, provider):
    # http://localhost:8000/v2/nodes/hacxp/files/?path=/55b055e04122ea42921d913b/&provider=osfstorage
    base = furl(API_BASE)
    base.path.segments = ['v2', 'nodes', str(node_id), 'files']
    base.args['path'] = path
    base.args['provider'] = provider
    return base.url




def wb_file_url(**kwargs):
    base = furl(WB_BASE)
    base.path.segments = ['file']
    base.args = kwargs
    return base.url

def wb_file_revisions():
    base = furl(WB_BASE)
    base.path.segments = ['revisions']
    return base.url


def wb_move_url():
    base = furl(WB_BASE)
    base.path.segments = ['ops','move']
    return base.url





