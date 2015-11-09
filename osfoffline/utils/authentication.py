import asyncio
import datetime
import furl
import logging

import aiohttp
import bcrypt
from PyQt5.QtWidgets import QMessageBox

from osfoffline import settings
from osfoffline.database_manager.db import session
from osfoffline.database_manager.models import User
from osfoffline.database_manager.utils import save
from osfoffline.polling_osf_manager.remote_objects import RemoteUser


def generate_hash(password):
    """ Generates a password hash using `bcrypt`.
        Number of rounds for salt generation is 12.

    :return: hashed password
    """
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt(12)
    )

token_request_body = json.load({
    'data': {
        'type': 'tokens',
        'attributes': {
            'name': 'OSF-Offline {}'.format(datetime.date.today()),
            'scopes': 'osf.full_write'
        }
    }
})


class AuthClient(object):
    """Manages authorization flow """
    def __init__(self):
        self.API_URL = furl.furl(settings.API_BASE)
        self.failed_login = False

    @asyncio.coroutine
    def _authenticate(self, username, password):
        """ Tries to use standard auth to authenticate and create a personal access token through APIv2

            :return: personal_access_token or None
        """
        token_url = furl.furl(settings.AUTH_BASE.format(username, password))
        token_url.path.add('/v2/tokens/create/')

        try:
            resp = yield from aiohttp.request(method='POST', url=token_url.url, data=token_request_body)
        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, aiohttp.errors.TimeoutError):
            # No internet connection
            self.display_error('Unable to connect to server. Check your internet connection or try again later.')
        except Exception as e:
            # Invalid credentials
            self.display_error('Invalid login credentials', e=e)
        else:
            if not resp.status == 201:
                return None
            json_resp = yield from resp.json()
            return json_resp['data']['attributes']['token_id']

    @asyncio.coroutine
    def _find_or_create_user(self, username, password):
        """ Checks to see if username exists in DB and compares password hashes.
            Tries to authenticate and create user if a valid user/oauth_token is not found.

        :return: user
        """
        try:
            user = session.query(User).filter(User.osf_login == username).one()

        except MultipleResultsFound:
            logging.warning('Multiple users with same username. deleting all users with this username. restarting function.')
            for user in session.query(User).filter(User.osf_login == username).all():
                session.delete(user)
                try:
                    save(session, user)
                except Exception as e:
                    self.display_error('Unable to save user data. Please try again later.', e=e)
            user = yield from self._find_or_create_user(username, password)

        except NoResultFound:
            logging.debug('User doesnt exist. Attempting to authenticate, then creating user.')
            personal_access_token = yield from self.authenticate(username, password)
            if not personal_access_token:
                self.failed_login = True
            else:
                user = User(
                    full_name='',
                    osf_id='',
                    osf_login=username,
                    osf_password=generate_hash(password),
                    osf_local_folder_path='',
                    oauth_token=personal_access_token,
                )

        finally:
            #Hit API_URL and populate more user data if possible
            if not user.oauth_token or user.password != generate_hash(password):
                logger.warning('Login error: User {} either has no oauth token or submitted a different password. Attempting to authenticate'.format(user))
                personal_access_token = yield from self.authenticate(username, password)
                if not personal_access_token:
                    self.failed_login = True
                else:
                    user.oauth_token = personal_access_token

            if not self.failed_login:
                yield from self._populate_user_data(user, username, password)
            else:
                return

    @asyncio.coroutine
    def _populate_user_data(self, user, username, password):
        """ Takes a user object, makes a request to ensure auth is working,
            and fills in any missing user data.

            :return: user
        """
        me = self.API_URL.path.add('/v2/users/me/')
        header = {'Authorization': 'Bearer {}'.format(user.oauth_token)}
        try:
            resp = yield from aiohttp.request(method='GET', url=me.url, headers=header)

        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, aiohttp.errors.TimeoutError):
            # No internet connection
            self.display_error('Unable to connect to server. Check your internet connection or try again later')

        except (aiohttp.errors.HttpBadRequest, aiohttp.errors.BadStatusLine):
            # Invalid credentials, delete possibly revoked PAT from user data and try again.
            # TODO: attempt to delete token from remote user data
            user.oauth_token = yield from self._authenticate(username, password)
            if not self.failed_login:
                yield from self._populate_user_data(user, username, password)
            else:
                return

        else:
            json_resp = yield from resp.json()
            remote_user = RemoteUser(json_resp['data'])
            user.full_name = remote_user.name
            user.osf_id = remote_user.id
            user.username = username
            user.password = generate_hash(password)

            return user

    @asyncio.coroutine
    def log_in(self, username=None, password=None):
        """ Takes standard auth credentials, returns authenticated user or none.
        """
        self.failed_login = False
        if not username or not password:
            raise ValueError('Username and password required for login.')

        user = yield from self._find_or_create_user(username, password)
        if failed_login:
            return
        if user:
            user.logged_in = True
            try:
                save(session, user)
            except Exception as e:
                self.display_error('Unable to save user data. Please try again later', e=e)
                return
            else:
                return user

        return

    def display_error(self, message, fail=True, e=None):
        """ Displays error message to user, sets fail flag unless otherwise specified,
            and logs exception if given.
        """
        if e:
            logging.exception(e)
        if fail:
            self.failed_login = True

        QMessageBox.warning(
            None,
            'Log in Failed',
            message
        )
