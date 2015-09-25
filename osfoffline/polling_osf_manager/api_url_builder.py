from osfoffline.settings import API_BASE
from furl import furl


#todo: can make a api_url_for function that makes things potentially simpler...?
USERS = 'users'
NODES = 'nodes'
FILES = 'files'
APPLICATIONS = 'applications'
CHILDREN = 'children'
def _ensure_trailing_slash(url):
    url.rstrip('/')
    return url+'/'

def api_url_for(endpoint_type, related_type=None, **kwargs):
    base = furl(API_BASE)
    assert endpoint_type in [USERS, NODES, FILES, APPLICATIONS]

    if endpoint_type == USERS:
        base.path.segments.extend(['v2',USERS])
        if 'user_id' in kwargs:
            base.path.segments.append(str(kwargs['user_id']))
        if related_type:
            assert related_type in [NODES]
            base.path.segments.append(related_type)
    elif endpoint_type == NODES:

        base.path.segments.extend(['v2',NODES])
        if 'node_id' in kwargs:
            base.path.segments.append(str(kwargs['node_id']))
        if related_type:
            assert related_type in [FILES, CHILDREN]
            base.path.segments.append(related_type)
            if 'provider' in kwargs and 'file_id' in kwargs:
                base.path.segments.extend([kwargs['provider'], str(kwargs['file_id'])])
    elif endpoint_type == FILES:
        base.path.segments.extend(['v2',FILES])
        if 'file_id' in kwargs:
            base.path.segments.append(str(kwargs['file_id']))

    return _ensure_trailing_slash(base.url)