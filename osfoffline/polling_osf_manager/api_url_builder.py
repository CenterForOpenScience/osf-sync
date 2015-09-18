from osfoffline.settings import API_BASE
from furl import furl


#todo: can make a api_url_for function that makes things potentially simpler...?
USERS = 'users'
NODES = 'nodes'
FILES = 'files'
APPLICATIONS = 'applications'
CHILDREN = 'children'
def api_url_for(endpoint_type, related_type=None, **kwargs):
    base = furl(API_BASE)
    assert endpoint_type in [USERS, NODES, FILES, APPLICATIONS]

    if endpoint_type == USERS:
        assert 'user_id' in kwargs.keys()
        base.path.segments.extend(['v2',USERS,str(kwargs['user_id'])])
        if related_type:
            assert related_type in [NODES]
            base.path.segments.extend([related_type])
        return base.url
    elif endpoint_type == NODES:
        assert 'node_id' in kwargs.keys()
        base.path.segments.extend(['v2',NODES,str(kwargs['node_id'])])
        if related_type:
            assert related_type in [FILES, CHILDREN]
            base.path.segments.extend([related_type])
            if 'provider' in kwargs and 'file_id' in kwargs:
                base.path.segments.extend([kwargs['provider'], str(kwargs['file_id'])])
        return base.url
    elif endpoint_type == FILES:
        assert 'file_id' in kwargs.keys()
        base.path.segments.extend(['v2',FILES,str(kwargs['file_id'])])
        return base.url