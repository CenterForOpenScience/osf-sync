from unittest import TestCase
from osfoffline.models import setup_db, User, Node, File, get_session, Base
from osfoffline.path import ProperPath
from watchdog.observers import Observer
from osfoffline.osf_event_handler import OSFEventHandler
from osfoffline.sync_local_filesytem_and_db import LocalDBSync
import asyncio

__author__ = 'himanshu'


class TestLocalDBSync(TestCase):
    def setUp(self):
        setup_db('home/himanshu/.local/share/OSF Offline')
        osf_folder = '/home/himanshu/OSF-Offline/osfoffline/sandbox/dumbdir/OSF/'
        user = User(osf_path=osf_folder)

        self.session = get_session()
        self.session.add(user)
        self.session.commit()

        observer = Observer()
        loop = asyncio.get_event_loop()
        event_handler = OSFEventHandler(osf_folder, '','',loop)
        observer.schedule(event_handler, osf_folder, recursive=True)

        self.sync = LocalDBSync(user.osf_local_folder_path, observer, user)

    def test_emit_new_events(self):
        self.fail()

    def test__make_local_db_tuple_list_both_None(self):
        local = None
        db = None
        local_db = self.sync._make_local_db_tuple_list(local, db)
        for local, db in local_db:
            if local is not None and db is not None:
                assert self._get_proper_path(local) == self._get_proper_path(db)
            elif local is not None:
                assert db is None
                assert isinstance(local, str)
            elif db is not None:
                assert isinstance(db, Base)
                assert local is None
            else:
                assert False

    def test__get_children(self):
        self.fail()

    def test__get_proper_path(self):
        self.fail()

    def test__represent_same_values(self):
        self.fail()

    def test__emit_new_events(self):
        self.fail()