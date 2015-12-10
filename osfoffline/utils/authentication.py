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
from osfoffline.exceptions import AuthError, TwoFactorRequiredError


def get_current_user():
    """
    Fetch the database object representing the currently active user
    :return: A user object (raises exception if none found)
    :rtype: models.User
    :raises SQLAlchemyError
    """
    return session.query(models.User).one()

class AuthClient(object):
    """Manages authorization flow """

    @asyncio.coroutine
    def _authenticate(self, username, password, *, otp=None):
        """ Tries to use standard auth to authenticate and create a personal access token through APIv2
            :param str or None otp: One time password used for two-factor authentication
            :return str: personal_access_token
            :raise AuthError or TwoFactorRequiredError
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

        if otp is not None:
            headers['X-OSF-OTP'] = otp

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
            # Regardless, will be prompted later with dialogbox later
            # TODO: narrow down possible exceptions here
            raise AuthError('Login failed')
        else:
            if resp.status == 401 or resp.status == 403:
                # If login failed because of a missing two-factor authentication code, notify the user to try again
                # This header appears for basic auth requests, and only when a valid password is provided
                otp_val= resp.headers.get('X-OSF-OTP', '')
                if otp_val.startswith('required'):
                    raise TwoFactorRequiredError('Must provide code for two-factor authentication')
                else:
                    raise AuthError('Invalid credentials')
            elif not resp.status == 201:
                raise AuthError('Invalid authorization response')
            else:
                json_resp = yield from resp.json()
                return json_resp['data']['attributes']['token_id']
        finally:
            yield from resp.release()

    @asyncio.coroutine
    def _create_user(self, username, password, personal_access_token):
        """ Tries to authenticate and create user.

        :return models.User: user
        :raise AuthError
        """
        logging.debug('User doesn\'t exist. Attempting to authenticate, then creating user.')

        user = models.User(
            id='',
            full_name='',
            login=username,
            oauth_token=personal_access_token,
        )
        return (yield from self.populate_user_data(user))

    @asyncio.coroutine
    def populate_user_data(self, user):
        """
        Takes a user object, makes a request to ensure auth is working,
        and fills in any missing user data.

        :return models.User: user
        :raise AuthError
        """
        me = furl.furl(settings.API_BASE)
        me.path.add('/v2/users/me/')
        header = {'Authorization': 'Bearer {}'.format(user.oauth_token)}
        try:
            # TODO: Update to use client/osf.py
            resp = yield from aiohttp.request(method='GET', url=me.url, headers=header)
        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, aiohttp.errors.TimeoutError):
            # No internet connection
            # TODO: Should this really be classified as an AuthError?
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
    def log_in(self, *, username=None, password=None, otp=None):
        """
        Log in with the provided credentials and return the database user object
        :param str username: The username / email address of the user
        :param str password: The password of the user
        :param str otp: One time password used for two-factor authentication
        :return models.User: A database object representing the logged-in user
        :raises: AuthError or TwoFactorRequiredError
        """
        if not username or not password:
            raise AuthError('Username and password required for login.')

        user = None
        try:
            user = get_current_user()
        except NoResultFound:
            pass

        personal_access_token = yield from self._authenticate(username, password, otp=otp)
        if user:
            if user.osf_login != username:
                # Different user authenticated, drop old user and allow login
                clear_models()
                # TODO: create_user should not need (always) need to call authenticate. Consolidate if possible.
                user = yield from self._create_user(username, password, personal_access_token)
            else:
                user.oauth_token = personal_access_token
        else:
            user = yield from self._create_user(username, password, personal_access_token)

        try:
            save(session, user)
        except SQLAlchemyError:
            raise AuthError('Unable to save user data. Please try again later')
        else:
            return user
