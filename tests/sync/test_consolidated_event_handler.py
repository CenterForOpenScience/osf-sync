import os

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

from osfoffline import settings

from tests.base import OSFOTestBase
from tests.utils import fail_after, unique_file_name
from tests.sync.utils import TestSyncWorker


class TestConsolidatedEventHandler(OSFOTestBase):

    # 'z_' because pytest fixtures are run in alphabetical order
    # h/t: http://stackoverflow.com/questions/25660064/in-which-order-are-pytest-fixtures-executed
    @pytest.fixture(scope="function", autouse=True)
    def z_attach_event_handler(self, request):
        self.sync_worker = TestSyncWorker(
            folder=self.root_dir
        )
        self.sync_worker.start()
        request.addfinalizer(self.sync_worker.stop)

    @fail_after(timeout=3)
    def test_create_file(self):
        project = self.PROJECT_STRUCTURE[0]
        osf_storage_path = os.path.join(
            self.root_dir,
            project['rel_path'],
            settings.OSF_STORAGE_FOLDER
        )
        file_name = unique_file_name()
        file_path = os.path.join(
            osf_storage_path,
            file_name
        )
        with open(file_path, 'w') as fp:
            fp.write('The meaning of life is 42')

        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._create_cache) == 1, \
            "exactly one event captured"
        assert isinstance(
            self.sync_worker._create_cache[0],
            FileCreatedEvent
        ) is True, \
            "the one captured event is a FileCreatedEvent"

    def test_update_file(self):
        project = self.PROJECT_STRUCTURE[0]
        import ipdb; ipdb.set_trace()
        file_path = os.path.join(
            self.root_dir,
            project['files'][0]['children'][0]['rel_path'].lstrip(os.path.sep)
        )
        os.utime(file_path, None)

        self.sync_worker.flushed.wait()
        assert len(self.sync_worker._event_cache.children()) == 1, \
            "exactly one event captured"
        assert isinstance(
            self._event_cache.children()[0],
            FileModifiedEvent
        ) is True, \
            "the one captured event is a FileModifiedEvent"

    def test_rename_file(self):
        pass

    def test_move_file(self):
        pass

    def test_delete_file(self):
        pass

    def test_create_folder(self):
        pass

    def test_rename_folder(self):
        pass

    def test_move_folder(self):
        pass

    def test_delete_folder(self):
        pass
