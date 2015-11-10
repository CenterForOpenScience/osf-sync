import asyncio
import datetime
import json
import logging

import aiohttp
import bcrypt
import furl
from PyQt5.QtWidgets import QMessageBox
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.exc import SQLAlchemyError

from osfoffline import settings
from osfoffline.database_manager.db import session
from osfoffline.database_manager.models import User
from osfoffline.database_manager.utils import save
from osfoffline.polling_osf_manager.remote_objects import RemoteUser


def generate_hash(password, salt=None):
    """ Generates a password hash using `bcrypt`.
        Number of rounds for salt generation is 12.
        Also used for checking passwords when salt
        is passed in.

    :param string password: password to hash
    :param hash salt:       stored hash of a password for comparison.
    :return:                hashed password
    """
    if not salt:
        salt = bcrypt.gensalt(12)
    return bcrypt.hashpw(
        password.encode('utf-8'),
        salt
    )

class AuthClient(object):
    """Manages authorization flow """
    def __init__(self):
        self.failed_login = False

    @asyncio.coroutine
    def _authenticate(self, username, password):
        """ Tries to use standard auth to authenticate and create a personal access token through APIv2

            :return: personal_access_token or None
        """
        token_url = furl.furl(settings.API_BASE)
        token_url.path.add('/v2/tokens/')
        token_request_body = '{"data": {"attributes": {"name": "OSF-Offline ' + \
            str(datetime.date.today()) + \
            '", "scopes": "' + settings.APPLICATION_SCOPES + \
            '"}, "type": "tokens"}}'
        headers = {'content-type': 'application/json'}

        try:
            resp = yield from aiohttp.request(method='POST', url=token_url.url, headers=headers, data=token_request_body, auth=(username, password))
        except (aiohttp.errors.ClientTimeoutError, aiohttp.errors.ClientConnectionError, aiohttp.errors.TimeoutError):
            # No internet connection
            self.display_error('Unable to connect to server. Check your internet connection or try again later.')
        except Exception as e:
            # Invalid credentials probably, but it's difficult to tell
            # Regadless, will be prompted later with dialogbox later
            # TODO: narrow down possible exceptions here
            logging.error(e.message)
        else:
            if not resp.status == 201:
                return None
            json_resp = yield from resp.json()
            return json_resp['data']['attributes']['token_id']

        return

    @asyncio.coroutine
    def _find_or_create_user(self, username, password):
        """ Checks to see if username exists in DB and compares password hashes.
            Tries to authenticate and create user if a valid user/oauth_token is not found.

        :return: user or None
        """
        user = None

        try:
            user = session.query(User).filter(User.osf_login == username).one()
        except MultipleResultsFound:
            logging.warning('Multiple users with same username. deleting all users with this username. restarting function.')
            for user in session.query(User).filter(User.osf_login == username).all():
                session.delete(user)
                try:
                    save(session, user)
                except SQLAlchemyError as e:
                    self.display_error('Unable to save user data. Please try again later.', exc=e.message)
            user = yield from self._find_or_create_user(username, password)
        except NoResultFound:
            logging.debug('User doesnt exist. Attempting to authenticate, then creating user.')
            personal_access_token = yield from self._authenticate(username, password)
            if not personal_access_token:
                self.failed_login = True
                return
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
            #Hit APIv2 and populate more user data if possible
            if not user:
                self.display_error('Invalid login credentials')
                return

            if not user.oauth_token or user.osf_password != generate_hash(password, user.osf_password):
                logging.warning('Login error: User {} either has no oauth token or submitted a different password. Attempting to authenticate'.format(user))
                personal_access_token = yield from self._authenticate(username, password)
                if not personal_access_token:
                    self.failed_login = True
                else:
                    user.oauth_token = personal_access_token

            if not self.failed_login:
                return (yield from self._populate_user_data(user, username, password))
            else:
                return

    @asyncio.coroutine
    def _populate_user_data(self, user, username, password):
        """ Takes a user object, makes a request to ensure auth is working,
            and fills in any missing user data.

            :return: user or None
        """
        me = furl.furl(settings.API_BASE)
        me.path.add('/v2/users/me/')
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
            self.display_error('Username and password required for login.')
            return
        user = yield from self._find_or_create_user(username, password)
        if self.failed_login:
            return
        if user:
            user.logged_in = True
            try:
                save(session, user)
            except SQLAlchemyError as e:
                self.display_error('Unable to save user data. Please try again later', exc=e.message)
                return
            else:
                return user

        return

    def display_error(self, message, fail=True, exc=None):
        """ Displays error message to user, sets fail flag unless otherwise specified,
            and logs exception if given.

            :param string message:  Message to be displayed to user
            :param Boolean fail:    Whether or not this error should abort login. Defaults to True
            :param string exc:      (Optional) Exception message
        """
        if exc:
            logging.error(exc)
        if fail:
            self.failed_login = True

        QMessageBox.warning(
            None,
            'Log in Failed',
            message
        )
