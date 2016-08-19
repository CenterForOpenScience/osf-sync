from pathlib import Path

from osfsync.sync.ext.auditor import Audit
from osfsync.sync.ext.auditor import Auditor
from osfsync.utils import EventType

from tests.base import OSFOTestBase


diff = Auditor._diff
# _diff never refers to self, so we'll always pass None as the fisrt argument

diff_dict = {
    '/file/path/as/string': Audit('fid', 'sha256', Path('/')),
}
base_path = Path('/fake/location/on/disk')
mock_paths = (
    base_path / 'README.md',
    base_path / 'data',
    base_path / 'data' / 'truth.csv',
    base_path / 'data' / 'lies.csv',
    base_path / 'data' / 'numbers.csv',
    base_path / 'data' / 'words.txt',
)

def tree_with_indexes(*idx):
    tree = {}
    for i in idx:
        path = mock_paths[i]
        tree[str(path)] = Audit(i, 'sha256-hash-' + str(i), path)
    return tree


class TestAuditor(OSFOTestBase):

    def test_diff(self):
        left = tree_with_indexes(0, 1, 2, 3, 4, 5)
        right = tree_with_indexes(0, 1, 2, 4, 5)
        # one file removed
        changes = diff(None, left, right)
        assert len(changes[EventType.MOVE]) == 0
        assert len(changes[EventType.CREATE]) == 1
        assert len(changes[EventType.UPDATE]) == 0
        assert len(changes[EventType.DELETE]) == 0
        assert str(mock_paths[3]) in changes[EventType.CREATE]
        # one file added
        changes = diff(None, right, left)
        assert len(changes[EventType.MOVE]) == 0
        assert len(changes[EventType.CREATE]) == 0
        assert len(changes[EventType.UPDATE]) == 0
        assert len(changes[EventType.DELETE]) == 1
        assert str(mock_paths[3]) in changes[EventType.DELETE]
        # two files removed
        right = tree_with_indexes(1, 2, 4, 5)
        changes = diff(None, left, right)
        assert len(changes[EventType.MOVE]) == 0
        assert len(changes[EventType.CREATE]) == 2
        assert len(changes[EventType.UPDATE]) == 0
        assert len(changes[EventType.DELETE]) == 0
        assert str(mock_paths[0]) in changes[EventType.CREATE]
        assert str(mock_paths[3]) in changes[EventType.CREATE]
