from osfoffline.settings import API_BASE, WB_BASE
import furl


def api_user_url(user_id):
    base = furl(API_BASE)
    base.path.segments = ['api','v2','users',user_id,'']
    return base.url

def api_user_nodes(user_id):
    base = furl(API_BASE)
    base.path.segments = ['api','v2','users',user_id, 'nodes', '']
    return base.url

def wb_file_url():
    base = furl(WB_BASE)
    base.path.segments = ['file']
    return base.url

def wb_file_revisions():
    base = furl(WB_BASE)
    base.path.segments = ['revisions']
    return base.url

def wb_move_url():
    base = furl(WB_BASE)
    base.path.segments = ['ops','move','']
    return base.url
