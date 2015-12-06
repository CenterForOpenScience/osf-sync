import asyncio
import datetime
import json
import logging

import aiohttp
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

    @asyncio.coroutine
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
            resp = yield from aiohttp.request(method='POST',
                                              url=token_url.url,
                                              headers=headers,
                                              data=json.dumps(token_request_body),
                                              auth=(username, password))
        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, aiohttp.errors.TimeoutError):
            # No internet connection
            raise AuthError('Unable to connect to server. Check your internet connection or try again later.')
        except Exception:
            # Invalid credentials probably, but it's difficult to tell
            # Regadless, will be prompted later with dialogbox later
            # TODO: narrow down possible exceptions here
            raise AuthError('Login failed')
        else:
            if resp.status == 401 or resp.status == 403:
                raise AuthError('Invalid credentials')
            elif not resp.status == 201:
                raise AuthError('Invalid authorization response')
            else:
                json_resp = yield from resp.json()
                return json_resp['data']['attributes']['token_id']
        finally:
            yield from resp.release()

    @asyncio.coroutine
    def _create_user(self, username, password):
        """ Tries to authenticate and create user.

        :return: user or raise AuthError
        """
        logging.debug('User doesnt exist. Attempting to authenticate, then creating user.')
        personal_access_token = yield from self._authenticate(username, password)

        user = models.User(
            id='',
            full_name='',
            login=username,
            oauth_token=personal_access_token,
        )
        return (yield from self.populate_user_data(user))

    @asyncio.coroutine
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
            resp = yield from aiohttp.request(method='GET', url=me.url, headers=header)
        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, aiohttp.errors.TimeoutError):
            # No internet connection
            raise AuthError('Unable to connect to server. Check your internet connection or try again later')
        except Exception:
            raise AuthError('Login failed. Please log in again.')
        else:
            if resp.status != 200:
                raise AuthError('Invalid credentials. Please log in again.')
            json_resp = yield from resp.json()
            data = json_resp['data']

            user.id = data['id']
            user.full_name = data['attributes']['full_name']

            return user
        finally:
            yield from resp.release()

    @asyncio.coroutine
    def log_in(self, *, username=None, password=None):
        """ Takes standard auth credentials, returns authenticated user or raises AuthError.
        """
        if not username or not password:
            raise AuthError('Username and password required for login.')

        user = None
        try:
            user = session.query(models.User).one()
        except NoResultFound:
            pass

        if user:
            user.oauth_token = yield from self._authenticate(username, password)
            if user.osf_login != username:
                # Different user authenticated, drop old user and allow login
                clear_models()
                user = yield from self._create_user(username, password)
        else:
            user = yield from self._create_user(username, password)

        try:
            save(session, user)
        except SQLAlchemyError:
            raise AuthError('Unable to save user data. Please try again later')
        else:
            return user
