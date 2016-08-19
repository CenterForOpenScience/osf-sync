import sys
import os
import shutil
from unittest import mock

import pytest

from watchdog.events import (  # noqa
    FileDeletedEvent,
    FileModifiedEvent,
    FileCreatedEvent,
    FileMovedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirCreatedEvent,
    DirMovedEvent
)

from osfsync import settings

from tests.base import OSFOTestBase
from tests.utils import unique_file_name, unique_folder_name
from tests.sync.utils import TestSyncWorker


class TestConsolidatedEventHandler(OSFOTestBase):

    # 'z_' because pytest fixtures are run in alphabetical order
    # h/t: http://stackoverflow.com/questions/25660064/in-which-order-are-pytest-fixtures-executed
    @pytest.fixture(scope="function", autouse=True)
    def z_attach_event_handler(self, request):
        self.sync_worker = TestSyncWorker(
            folder=str(self.root_dir)
        )
        self.sync_worker.start()
        def stop():
            self.sync_worker.stop()
            self.sync_worker.flushed.clear()
            self.sync_worker.done.set()
            self.sync_worker.done.clear()
            self.sync_worker.join()
        request.addfinalizer(stop)
        self.sync_worker.observer.ready.wait()

    def test_create_file(self):
        project = self.PROJECT_STRUCTURE[0]
        osf_storage_path = self.root_dir.join(
            project['rel_path'].lstrip(os.path.sep),
            settings.OSF_STORAGE_FOLDER
        )
        file_name = unique_file_name()
        file_path = osf_storage_path.join(
            file_name
        )
        with open(str(file_path), 'w') as fp:
            fp.write('The meaning of life is 42')

        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], FileCreatedEvent) is True, 'the one captured event is a FileCreatedEvent'

    def test_update_file(self):
        project = self.PROJECT_STRUCTURE[0]
        file_path = self.root_dir.join(
            project['files'][0]['children'][0]['rel_path'].lstrip(os.path.sep)
        )
        with open(str(file_path), 'w') as fp:
            fp.write('Hello world')
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], FileModifiedEvent) is True, 'the one captured event is a FileModifiedEvent'

    @mock.patch('osfsync.sync.ext.watchdog.sha256_from_event')
    def test_rename_file(self, sha_mock):
        sha_mock.return_value = '1234'
        project = self.PROJECT_STRUCTURE[0]
        file_path = self.root_dir.join(
            project['files'][0]['children'][0]['rel_path'].lstrip(os.path.sep)
        )
        os.rename(str(file_path), 'foobar.baz')
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], FileMovedEvent) is True, 'the one captured event is a FileMovedEvent'

    def test_move_file(self):
        project = self.PROJECT_STRUCTURE[0]
        file_path = self.root_dir.join(
            project['files'][0]['children'][0]['rel_path'].lstrip(os.path.sep)
        )
        new_path = str(file_path).replace(file_path.basename, 'foo.bar')
        shutil.move(str(file_path), new_path)
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], FileMovedEvent) is True, 'the one captured event is a FileMovedEvent'

    def test_delete_file(self):
        project = self.PROJECT_STRUCTURE[0]
        file_path = self.root_dir.join(
            project['files'][0]['children'][0]['rel_path'].lstrip(os.path.sep)
        )
        os.remove(str(file_path))
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], FileDeletedEvent) is True, 'the one captured event is a FileDeletedEvent'

    def test_create_folder(self):
        project = self.PROJECT_STRUCTURE[0]
        parent_dir_path = self.root_dir.join(
            project['files'][0]['rel_path'].lstrip(os.path.sep)
        )
        dir_path = os.path.join(
            str(parent_dir_path),
            unique_folder_name()
        )
        os.mkdir(dir_path)
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], DirCreatedEvent) is True, 'the one captured event is a DirCreatedEvent'

    def test_create_folder_with_contents(self):
        project = self.PROJECT_STRUCTURE[0]
        parent_dir_path = self.root_dir.join(
            project['files'][0]['rel_path'].lstrip(os.path.sep)
        )

        super_root_dir = self.root_dir.dirpath()
        ext_folder = super_root_dir.mkdir('ext')
        ext_child_path = ext_folder.join('ext_child')
        with open(str(ext_child_path), 'w') as fp:
            fp.write('Hello, world')

        shutil.move(str(ext_folder), str(parent_dir_path) + os.path.sep)
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 2, 'exactly two events captured'
        create_cache = self.sync_worker._event_cache.events
        assert isinstance(create_cache[0], DirCreatedEvent) is True, 'the first event is a DirCreatedEvent'
        assert isinstance(create_cache[1], FileCreatedEvent) is True, 'the s event is a DirCreatedEvent'

    def test_rename_folder(self):
        project = self.PROJECT_STRUCTURE[0]
        dir_path = self.root_dir.join(
            project['files'][0]['rel_path'].lstrip(os.path.sep)
        )
        new_dir_path = str(dir_path).replace(dir_path.basename, 'newdir')
        os.rename(str(dir_path), new_dir_path)
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], DirMovedEvent) is True, 'the one captured event is a DirMovedEvent'

    def test_move_folder(self):
        project = self.PROJECT_STRUCTURE[0]
        dir_path = self.root_dir.join(
            project['files'][0]['rel_path'].lstrip(os.path.sep)
        )
        new_dir_path = str(dir_path).replace(dir_path.basename, 'newdir')
        shutil.move(str(dir_path), new_dir_path)
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], DirMovedEvent) is True, 'the one captured event is a DirMovedEvent'

    def test_delete_folder(self):
        project = self.PROJECT_STRUCTURE[0]
        dir_path = self.root_dir.join(
            project['files'][1]['rel_path'].lstrip(os.path.sep)
        )
        shutil.rmtree(str(dir_path))
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], DirDeletedEvent) or (isinstance(self.sync_worker._event_cache.events[0], FileDeletedEvent) and sys.platform == 'win32'), 'the one captured event is a DirDeletedEvent'

    def test_delete_folder_with_children(self):
        project = self.PROJECT_STRUCTURE[0]
        dir_path = self.root_dir.join(
            project['files'][0]['rel_path'].lstrip(os.path.sep)
        )
        shutil.rmtree(str(dir_path))
        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.events) == 1, 'exactly one event captured'
        assert isinstance(self.sync_worker._event_cache.events[0], DirDeletedEvent) is True, 'the one captured event is a DirDeletedEvent'
