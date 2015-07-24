import json
from osfoffline.settings import API_BASE, WB_BASE
from osfoffline.polling_osf_manager.api_url_builder import api_user_nodes
user={
    "data": {
        "id": "1",
        "fullname": "himanshu",
        "given_name": "himanshu",
        "middle_name": "",
        "family_name": "",
        "suffix": "",
        "date_registered": "2015-07-06T17:51:22.833000",
        "gravatar_url": "https://secure.gravatar.com/avatar/7241b93c02e7d393e5f118511880734a?d=identicon&size=40",
        "employment_institutions": [],
        "educational_institutions": [],
        "social_accounts": {},
        "links": {
            "nodes": {
                "relation": "http://localhost:8000/v2/users/5bqt9/nodes/"
            },
            "html": "http://localhost:5000/5bqt9/",
            "self": "http://localhost:8000/v2/users/5bqt9/"
        },
        "type": "users"
    }
}

def get_user_response(id, fullname):
    user['data']['id'] = id
    user['data']['fullname']=fullname
    user['data']['given_name']=fullname
    user['data']['links']['nodes']['relation']=api_user_nodes(id)
    return json.dumps(user)





