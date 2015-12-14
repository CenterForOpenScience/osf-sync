import datetime
import json
import logging

import requests
import furl
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound


from osfoffline import settings

from osfoffline.database import clear_models, session
from osfoffline.database import models
from osfoffline.database.utils import save
from osfoffline.exceptions import AuthError


def get_current_user():
    """
    Fetch the database object representing the currently active user
    :return: A user object (raises exception if none found)
    :rtype: User
    :raises SQLAlchemyError
    """
    return session.query(models.User).one()


class AuthClient(object):
    """Manages authorization flow """

    def _authenticate(self, username, password):
        """ Tries to use standard auth to authenticate and create a personal access token through APIv2

            :return: personal_access_token or raise AuthError
        """
        token_url = furl.furl(settings.API_BASE)
        token_url.path.add('/v2/tokens/')
        token_request_body = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'OSF-Offline - {}'.format(datetime.date.today()),
                    'scopes': settings.APPLICATION_SCOPES
                }
            }
        }
        headers = {'content-type': 'application/json'}

        try:
            resp = requests.post(
                token_url.url,
                headers=headers,
                data=json.dumps(token_request_body),
                auth=(username, password)
            )
        except Exception:
            # Invalid credentials probably, but it's difficult to tell
            # Regadless, will be prompted later with dialogbox later
            # TODO: narrow down possible exceptions here
            raise AuthError('Login failed')
        else:
            if resp.status_code in (401, 403):
                raise AuthError('Invalid credentials')
            elif not resp.status_code == 201:
                raise AuthError('Invalid authorization response')
            else:
                json_resp = resp.json()
                return json_resp['data']['attributes']['token_id']

    def _create_user(self, username, password):
        """ Tries to authenticate and create user.

        :return: user or raise AuthError
        """
        logging.debug('User doesnt exist. Attempting to authenticate, then creating user.')
        personal_access_token = self._authenticate(username, password)

        user = models.User(
            id='',
            full_name='',
            login=username,
            oauth_token=personal_access_token,
        )
        return self.populate_user_data(user)

    def populate_user_data(self, user):
        """ Takes a user object, makes a request to ensure auth is working,
            and fills in any missing user data.

            :return: user or raise AuthError
        """
        me = furl.furl(settings.API_BASE)
        me.path.add('/v2/users/me/')
        header = {'Authorization': 'Bearer {}'.format(user.oauth_token)}
        try:
            # TODO: Update to use client/osf.py
            resp = requests.get(me.url, headers=header)
        except Exception:
            raise AuthError('Login failed. Please log in again.')
        else:
            if resp.status_code != 200:
                raise AuthError('Invalid credentials. Please log in again.')
            json_resp = resp.json()
            data = json_resp['data']

            user.id = data['id']
            user.full_name = data['attributes']['full_name']

            return user

    def login(self, *, username=None, password=None):
        """ Takes standard auth credentials, returns authenticated user or raises AuthError.
        """
        if not username or not password:
            raise AuthError('Username and password required for login.')

        try:
            user = session.query(models.User).one()
        except NoResultFound:
            user = None

        if user:
            user.oauth_token = self._authenticate(username, password)
            if user.osf_login != username:
                # Different user authenticated, drop old user and allow login
                clear_models()
                user = self._create_user(username, password)
        else:
            user = self._create_user(username, password)

        try:
            save(session, user)
        except SQLAlchemyError:
            raise AuthError('Unable to save user data. Please try again later')
        return user
