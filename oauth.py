"""
Flask application. Modeled in part on https://requests-oauthlib.readthedocs.org/en/latest/#overview

This is a demonstration application, only. This is not the recommended way to handle secret info in production,
    and contains minimal error handling at best.
"""
__author__ = 'andyboughton'

import os

import furl

from flask import Flask, abort, redirect, request, session, url_for
import requests
from requests_oauthlib import OAuth2Session

CLIENT_ID = 'eb53366f1ef347e3a7dde94cae4896be'
CLIENT_SECRET = 'iUny91itQg8hBneJZfU5yLLnvKdQfBYjdPLjvpLX'
REDIRECT_URI = 'http://localhost:5001/oauth_callback/'

API_BASE_URL = 'https://staging-api.osf.io/v2'
AUTH_BASE_URL = 'https://staging-accounts.osf.io/oauth2/authorize'
TOKEN_REQUEST_URL = 'https://staging-accounts.osf.io/oauth2/token'
TOKEN_REFRESH_URL = TOKEN_REQUEST_URL

app = Flask(__name__)


#### Utility functions
def token_updater(token):
    """Store the newest version of the token"""
    session['oauth_token'] = token


def get_request_client(token_dict):
    """
    DRY request client
    :param token_dict: Token data returned from OAuth server (including access and refresh tokens)
    :return: Preconfigured oauth2 client
    """
    refresh_kwargs = {'client_id': CLIENT_ID,
                      'client_secret': CLIENT_SECRET,
                      'redirect_uri': REDIRECT_URI}

    client = OAuth2Session(CLIENT_ID,
                           redirect_uri=REDIRECT_URI,
                           token=token_dict,
                           auto_refresh_url=TOKEN_REFRESH_URL,
                           auto_refresh_kwargs=refresh_kwargs,
                           token_updater=token_updater)
    return client


#### API Handlers
def api_v2_url(path_str,
               params=None,
               base_route=API_BASE_URL,
               **kwargs):
    """
    Convenience function for APIv2 usage: Concatenates parts of the absolute API url based on arguments provided

    For example: given path_str = '/nodes/abcd3/contributors/' and params {'filter[fullname]': 'bob'},
        this function would return the following on the local staging environment:
        'http://localhost:8000/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob'

    This is NOT a full lookup function. It does not verify that a route actually exists to match the path_str given.
    """
    params = params or {}  # Optional params dict for special-character param names, eg filter[fullname]

    base_url = furl.furl(base_route)
    sub_url = furl.furl(path_str)

    base_url.path.add(sub_url.path.segments)

    base_url.args.update(params)
    base_url.args.update(kwargs)
    return str(base_url)


class ApiV2(object):
    """
    Mock class for OSF APIv2 calls. Can pass in a preconfigured client for OAuth usage.

    :param client: A `requests`-like object for making API calls.
    """

    def __init__(self, client=None):
        self.client = client or requests

    def get_user_id(self):
        url = api_v2_url("/users/me")
        res = self.client.get(url)
        data = res.json()['data']

        return data['id']

    def get_projects_count(self, filters=None):
        url = api_v2_url('/users/me/nodes', params=filters)
        res = self.client.get(url)
        return res.json()['links']['meta']['total']


#### Routes
@app.route('/', methods=['GET'])
def home():
    """Display auth screen, or redirect to the action, as appropriate"""
    token = session.get('oauth_token')
    if token is None:
        return redirect(url_for('login'))
    return redirect(url_for('graph_projects'))


@app.route('/login/', methods=['GET'])
def login():
    import ipdb;
    ipdb.set_trace()
    osf = OAuth2Session(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI)
    authorization_url, state = osf.authorization_url(AUTH_BASE_URL, client_secret=CLIENT_SECRET,
                                                     approval_prompt='force')
    # session['oauth_state'] = state
    return redirect(authorization_url)


@app.route('/callback/', methods=['GET'])
def callback():
    """The oauth app redirects the user here; perform logic to fetch access token and redirect to a target url"""
    osf = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session['oauth_state'])
    auth_response = request.url

    # TODO: The token request fails (with CAS errors) when redirect_uri is not specified; is this a CAS bug?
    token = osf.fetch_token(TOKEN_REQUEST_URL,
                            client_secret=CLIENT_SECRET,
                            authorization_response=auth_response,
                            verify=False)

    token_updater(token)
    return redirect(url_for("graph_projects"))


@app.route('/graph/', methods=['GET'])
def graph_projects():
    """If the user is logged in and has registered an access token, perform queries"""
    token = session.get('oauth_token')
    if token is None:
        # Login page indirectly redirects here; don't create a circular redirect.
        abort(403)

    client = get_request_client(token)
    api = ApiV2(client=client)

    public_count = api.get_projects_count(filters={'filter[public]': 'true'})
    private_count = api.get_projects_count(filters={'filter[public]': 'false'})

    # TODO: Make this a graph
    return "You're logged in! You have {} public and {} private projects".format(public_count, private_count)


if __name__ == '__main__':
    # For local development *only*: disable the HTTPS requirement. Don't do this in production. Really.
    # app.config.from_pyfile('settings.py')

    os.environ['DEBUG'] = '1'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    base = furl.furl('http://staging-accounts.osf.io/oauth2/authorize')
    base.args['response_type'] = 'code'
    base.args['client_id'] = CLIENT_ID
    base.args['redirect_uri'] = REDIRECT_URI
    # base.args['scope'] = 'accessTokenScope'
    base.args['state'] = 'randomphrase'
    base.args['access_type'] = 'offline'
    base.args['approval_prompt'] = 'force'
    # rsp = requests.get(base.url)
    import webbrowser

    print(base.url)
    webbrowser.open_new_tab(base.url)

    # response_type=token&client_id=gJgfkHAtz&redirect_uri=https://my-application/oauth/callback/osf/&scope=user.profile&state=FSyUOBgWiki_hyaBsa
    base = furl.furl('http://staging-accounts.osf.io/oauth2/authorize')
    base.args['response_type'] = 'token'
    base.args['client_id'] = CLIENT_ID
    base.args['redirect_uri'] = REDIRECT_URI
    base.args['scope'] = 'user.profile'
    base.args['state'] = 'randomphrase'
    # base.args['access_type'] = 'offline'
    # base.args['approval_prompt'] = 'force'
    # rsp = requests.get(base.url)
    import webbrowser

    print(base.url)
    webbrowser.open_new_tab(base.url)


    # get_request_client()

    # oauth_token = '56310306029bdb6c75085301.3ErHvoWHZRFbPzOmrwF52NvT9Ic'
    # resp = requests.get('https://accounts.osf.io/oauth2/profile', headers={'Authorization':'Bearer {}'.format(oauth_token)},cookies={'osf_staging':oauth_token})
    # print(resp.text)
    app.run(port=5001)
