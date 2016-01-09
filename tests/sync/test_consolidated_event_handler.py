import os

import pytest

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
        assert len(self.sync_worker._create_cache) == 1
        # TODO: not really necessary because the TestSyncWorker is not a
        # Singleton and is reinstantiate for every test.
        self.sync_worker.flushed.clear()
        self.sync_worker.done.set()

    def test_update_file(self):
        pass

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
