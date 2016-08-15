import pytest

import os
import sys
import time
from pathlib import Path

from watchdog import events

from osfoffline import utils
from osfoffline.tasks import operations
from osfoffline.utils.log import start_logging
from osfoffline.sync.utils import EventConsolidator

from tests.sync.utils import TestSyncObserver


start_logging()


_map = {
    ('move', True): events.DirMovedEvent,
    ('move', False): events.FileMovedEvent,
    ('modify', True): events.DirModifiedEvent,
    ('modify', False): events.FileModifiedEvent,
    ('delete', True): events.DirDeletedEvent,
    ('delete', False): events.FileDeletedEvent,
    ('create', True): events.DirCreatedEvent,
    ('create', False): events.FileCreatedEvent,
}


def Event(type_, *src, sha=None):
    assert len(src) < 3
    if len(src) > 1:
        assert src[0].endswith('/') == src[1].endswith('/')
    event = _map[(type_, src[0].endswith('/'))](*(x.rstrip('/').replace('/', os.path.sep) for x in src))
    event.sha256 = sha
    return event


CASES = [{
    'input': [Event('modify', '/Foo/bar/')],
    'output': []
}, {
    'input': [Event('move', '/Foo/bar', '/Foo/baz')],
    'output': [Event('move', '/Foo/bar', '/Foo/baz')]
}, {
    'input': [Event('move', '/Foo/bar/', '/Foo/baz/')],
    'output': [Event('move', '/Foo/bar/', '/Foo/baz/')]
}, {
    'input': [
        Event('move', '/Foo/bar/', '/Foo/baz/'),
        Event('move', '/Foo/bar/file.txt', '/Foo/baz/file.txt')
    ],
    'output': [Event('move', '/Foo/bar/', '/Foo/baz/')]
}, {
    'input': [
        Event('move', '/Foo/bar/file.txt', '/Foo/baz/file.txt'),
        Event('move', '/Foo/bar/', '/Foo/baz/')
    ],
    'output': [Event('move', '/Foo/bar/', '/Foo/baz/')]
}, {

######## Consolidation for same events #########################
    'input': [
        Event('move', '/parent/', '/george/'),
        Event('move', '/parent/child/', '/george/child/'),
        Event('move', '/parent/file.txt', '/george/file.txt'),
        Event('move', '/parent/child/file.txt', '/george/child/file.txt'),
        Event('move', '/parent/child/grandchild/', '/george/child/grandchild/'),
        Event('move', '/parent/child/grandchild/file.txt', '/george/child/grandchild/file.txt'),
    ],
    'output': [Event('move', '/parent/', '/george/')]
}, {
    'input': [
        Event('move', '/parent/', '/george/'),
        Event('move', '/parent/child/', '/george/child/'),
        Event('move', '/parent/child/grandchild/', '/george/child/grandchild/'),
    ],
    'output': [Event('move', '/parent/', '/george/')]
}, {
    'input': [
        Event('delete', '/parent/'),
        Event('delete', '/parent/child/'),
        Event('delete', '/parent/file.txt'),
        Event('delete', '/parent/child/file.txt'),
        Event('delete', '/parent/child/grandchild/'),
        Event('delete', '/parent/child/grandchild/file.txt')
    ],
    'output': [Event('delete', '/parent/')]
}, {
    'input': [
        Event('delete', '/parent/'),
        Event('delete', '/parent/child/'),
        Event('delete', '/parent/child/grandchild/'),
    ],
    'output': [Event('delete', '/parent/')]
}, {

######## Does not consolidate file events   #########################
    'input': [
        Event('create', '/parent/'),
        Event('create', '/parent/file.txt'),
    ],
    'output': [
        Event('create', '/parent/'),
        Event('create', '/parent/file.txt'),
    ],
}, {
    'input': [
        Event('move', '/parent/file.txt', '/george/file.txt', sha=b'123'),
        Event('move', '/parent/child/file.txt', '/george/child/file.txt', sha=b'456'),
        Event('move', '/parent/child/grandchild/file.txt', '/george/child/grandchild/file.txt', sha=b'789'),
    ],
    'output': [
        Event('move', '/parent/file.txt', '/george/file.txt'),
        Event('move', '/parent/child/grandchild/file.txt', '/george/child/grandchild/file.txt'),
        Event('move', '/parent/child/file.txt', '/george/child/file.txt'),
    ]
}, {
    'input': [
        Event('delete', '/parent/file.txt'),
        Event('delete', '/parent/child/file.txt'),
        Event('delete', '/parent/child/grandchild/file.txt')
    ],
    'output': [
        Event('delete', '/parent/file.txt'),
        Event('delete', '/parent/child/grandchild/file.txt'),
        Event('delete', '/parent/child/file.txt'),
    ],
}, {

######## Consolidation for differing events #########################
    'input': [
        Event('delete', '/file.txt'),
        Event('create', '/file.txt'),
    ],
    # 'output': [Event('modify', '/file.txt')]
    'output': [Event('create', '/file.txt')]
}, {
    'input': [
        Event('delete', '/folder/'),
        Event('create', '/folder/'),
    ],
    'output': [
        # Event('delete', '/folder/'),
        Event('create', '/folder/'),
    ]
}, {
    'input': [
        Event('modify', '/file.txt'),
        Event('delete', '/file.txt'),
    ],
    'output': [
        Event('delete', '/file.txt'),
    ]
}, {
    'input': [
        Event('create', '/file.txt'),
        Event('delete', '/file.txt'),
    ],
    'output': []
}, {
    'input': [
        Event('move', '/file.txt', '/other_file.txt'),
        Event('delete', '/other_file.txt'),
    ],
    'output': [Event('delete', '/file.txt')]
}, {
    'input': [
        Event('move', '/folder1/file.txt', '/folder1/other_file.txt'),
        Event('delete', '/folder1/'),
    ],
    'output': [Event('delete', '/folder1/')]
}, {
    'input': [
        Event('create', '/file.txt'),
        Event('move', '/file.txt', '/other_file.txt'),
        Event('delete', '/other_file.txt'),
    ],
    'output': []
}, {
    'input': [
        Event('create', '/folder/'),
        Event('create', '/folder/file.txt'),
        Event('delete', '/folder/'),
    ],
    'output': []
}, {
    'input': [
        Event('modify', '/parent/file.txt'),
        Event('modify', '/parent/'),
    ],
    'output': [Event('modify', '/parent/file.txt')]
}, {
    'input': [
        Event('create', '/file.txt'),
        Event('move', '/file.txt', '/test.txt'),
    ],
    'output': [Event('create', '/test.txt')]
}, {

######## Test for directory with the same prefix as #######
    'input': [
        Event('delete', '/qwer'),
        Event('delete', '/qwerdir/'),
    ],
    'output': [
        Event('delete', '/qwerdir/'),
        Event('delete', '/qwer'),
    ]
}, {

######## Weird cases Word/Vim/Tempfiles ############################
    'input': [
        Event('create', '/~WRL0001.tmp'),
        Event('modify', '/~WRL0001.tmp'),
        Event('move', '/file.docx', '/~WRL0005.tmp', sha=b'123'),
        Event('move', '/~WRL0001.tmp', '/file.docx', sha=b'456'),
        Event('delete', '/~WRL0005.tmp'),
    ],
    # 'output': [Event('modify', '/file.docx')],
    'output': [Event('create', '/file.docx')],
}, {
    'input': [
        Event('create', '/osfoffline.py'),
        Event('modify', '/osfoffline.py'),
    ],
    'output': [Event('create', '/osfoffline.py')],
}, {
    'input': [
        Event('modify', '/folder/donut.txt'),
        Event('move', '/folder/donut.txt', '/test/donut.txt'),
        Event('move', '/folder/', '/test/'),
    ],
    'output': [
        Event('move', '/folder/', '/test/'),
        Event('modify', '/test/donut.txt'),
    ],
}, {
    'input': [
        Event('move', '/folder/donut.txt', '/other_folder/bagel.txt', sha='1234'),
        Event('move', '/folder/', '/test/'),
    ],
    'output': [
        Event('move', '/folder/donut.txt', '/other_folder/bagel.txt'),
        Event('move', '/folder/', '/test/'),
    ],
}, {
    'input': [
        Event('modify', '/donut.txt'),
        Event('move', '/donut.txt', '/bagel.txt'),
    ],
    'output': [
        Event('move', '/donut.txt', '/bagel.txt'),
        Event('modify', '/bagel.txt'),
    ],
}, {

########## Generate one offs just to be certain ####################
    'input': [Event('modify', '/folder/donut.txt')],
    'output': [Event('modify', '/folder/donut.txt')],
}, {
    'input': [Event('modify', '/folder/donut/')],
    'output': [],
}, {
    'input': [Event('delete', '/folder/donut.txt')],
    'output': [Event('delete', '/folder/donut.txt')],
}, {
    'input': [Event('delete', '/folder/donut/')],
    'output': [Event('delete', '/folder/donut/')],
}, {
    'input': [Event('create', '/folder/donut.txt')],
    'output': [Event('create', '/folder/donut.txt')],
}, {
    'input': [Event('create', '/folder/donut/')],
    'output': [Event('create', '/folder/donut/')],
}, {
    'input': [
        Event('create', '/bagel.txt', sha=b'123'),
        Event('delete', '/donut.txt', sha=b'123'),
    ],
    'output': [Event('move', '/donut.txt', '/bagel.txt')]
}, {
    'input': [
        Event('create', '/bagel.txt', sha=b'123'),
        Event('delete', '/donut.txt', sha=b'123'),
        Event('create', '/a/cake.txt', sha=b'456'),
        Event('delete', '/a/cup.txt', sha=b'456'),
        Event('create', '/a/b/shake.txt', sha=b'789'),
        Event('delete', '/a/b/milk.txt', sha=b'789'),
    ],
    'output': [
        Event('move', '/donut.txt', '/bagel.txt'),
        Event('move', '/a/cup.txt', '/a/cake.txt'),
        Event('move', '/a/b/milk.txt', '/a/b/shake.txt'),
    ]
}, {
    'delay': None if sys.platform == 'win32' else 0.75,
    'input': [
        Event('create', '/untitled/'),
        Event('move', '/untitled/', '/newfolder/'),
        Event('move', '/donut.txt', '/newfolder/donut.txt'),
        Event('move', '/bagel.txt', '/newfolder/bagel.txt'),
    ],
    'output': [
        Event('create', '/newfolder/'),
        Event('move', '/donut.txt', '/newfolder/donut.txt'),
        Event('move', '/bagel.txt', '/newfolder/bagel.txt'),
    ]
}, {
    'delay': None if sys.platform == 'win32' else 0.75,
    'input': [
        Event('create', '/untitled/'),
        Event('move', '/untitled/', '/newfolder/'),
        Event('move', '/child/', '/newfolder/child/'),
    ],
    'output': [
        Event('create', '/newfolder/'),
        Event('move', '/child/', '/newfolder/child/'),
    ]
}, {
    'delay': None if sys.platform == 'win32' else 0.75,
    'input': [
        Event('create', '/parent/untitled/'),
        Event('move', '/parent/untitled/', '/parent/newfolder/'),
        Event('move', '/child/', '/parent/newfolder/child/'),
    ],
    'output': [
        Event('create', '/parent/newfolder/'),
        Event('move', '/child/', '/parent/newfolder/child/'),
    ]
}, {
    'delay': None if sys.platform == 'win32' else 0.75,
    'input': [
        Event('move', '/untitled/', '/newfolder/'),
        Event('move', '/donut.txt', '/newfolder/donut.txt'),
        Event('move', '/bagel.txt', '/newfolder/bagel.txt'),
    ],
    'output': [
        Event('move', '/untitled/', '/newfolder/'),
        Event('move', '/donut.txt', '/newfolder/donut.txt'),
        Event('move', '/bagel.txt', '/newfolder/bagel.txt'),
    ]
}, {
    'input': [
        Event('move', '/untitled/', '/newfolder/'),
        Event('delete', '/newfolder/')
    ],
    'output': [
        Event('delete', '/untitled/'),
    ]
}, {
    'delay': None if sys.platform == 'win32' else 0.75,
    'input': [
        Event('move', '/olddir/', '/newdir/'),
        Event('move', '/donut003.txt', '/newdir/donut003.txt'),
        Event('move', '/donut004.txt', '/newdir/donut004.txt'),
    ],
    'output': [
        Event('move', '/olddir/', '/newdir/'),
        Event('move', '/donut004.txt', '/newdir/donut004.txt'),
        Event('move', '/donut003.txt', '/newdir/donut003.txt'),
    ]
}]


# List of tests that can't be easily parsed by the integration tester
UNIT_ONLY = [{
    'input': [
        Event('move', '/untitled/', '/newfolder/'),
        Event('move', '/newfolder/otherfolder/', '/otherfolder/'),
    ],
    'output': [
        Event('move', '/untitled/', '/newfolder/'),
        Event('move', '/newfolder/otherfolder/', '/otherfolder/'),
    ]
# }, {
#     'input': [
#         Event('create', '/untitled/'),
#         Event('move', '/untitled/', '/newfolder/'),
#         Event('move', '/untitled/file.txt', '/newfolder/file.txt', sha=b'123'),
#         Event('delete', '/file.txt', sha=b'123'),
#     ],
#     'output': [
#         Event('create', '/newfolder/'),
#         Event('move', '/file.txt', '/newfolder/file.txt'),
#     ]
}]


TMP_CASES = [{
    'input': [Event('create', '/~$file.txt')],
    'output': []
}, {
    'input': [Event('move', '/myfile.txt', '/~$file.txt')],
    'output': [Event('delete', '/myfile.txt')]
}, {
    'input': [Event('delete', '/file.tmp')],
    'output': []
}, {
    'input': [Event('modify', '/.DS_Store')],
    'output': []
}]


CONTEXT_EVENT_MAP = {
    events.FileCreatedEvent: operations.RemoteCreateFile,
    events.FileDeletedEvent: operations.RemoteDeleteFile,
    events.FileModifiedEvent: operations.RemoteUpdateFile,
    events.FileMovedEvent: operations.RemoteMoveFile,
    events.DirCreatedEvent: operations.RemoteCreateFolder,
    events.DirDeletedEvent: operations.RemoteDeleteFolder,
    events.DirMovedEvent: operations.RemoteMoveFolder,
}


class TestEventConsolidator:

    @pytest.mark.parametrize('input, expected', [(case['input'], case['output']) for case in CASES + UNIT_ONLY])
    def test_event_consolidator(self, input, expected):
        consolidator = EventConsolidator(ignore=False)
        for event in input:
            consolidator.push(event)
        assert list(consolidator.events) == list(expected)

    def test_event_consolidator_windows_folder_delete(self):
        input = [
            Event('modify', 'parent'),
            Event('delete', 'parent/child.txt'),
            Event('delete', 'parent'),
        ]
        expected = [Event('delete', 'parent/')]

        consolidator = EventConsolidator(ignore=False)
        for event in input:
            consolidator.push(event)
        assert list(consolidator.events) == list(expected)

    @pytest.mark.parametrize('input, expected', [(case['input'], case['output']) for case in TMP_CASES])
    def test_event_consolidator_temp_files(self, input, expected):
        consolidator = EventConsolidator()
        for event in input:
            consolidator.push(event)
        assert list(consolidator.events) == list(expected)


class TestObserver:

    def perform(self, tmpdir, event):
        if isinstance(event, events.FileModifiedEvent):
            with tmpdir.join(event.src_path).open('ab') as fobj:
                fobj.write(event.sha256 or os.urandom(50))
        elif isinstance(event, events.FileCreatedEvent):
            with tmpdir.join(event.src_path).open('wb+') as fobj:
                fobj.write(event.sha256 or os.urandom(50))
        elif isinstance(event, events.DirModifiedEvent):
            return
        elif isinstance(event, (events.FileMovedEvent, events.DirMovedEvent)):
            tmpdir.join(event.src_path).move(tmpdir.join(event.dest_path))
        elif isinstance(event, (events.DirDeletedEvent, events.FileDeletedEvent)):
            tmpdir.join(event.src_path).remove()
        elif isinstance(event, events.DirCreatedEvent):
            tmpdir.ensure(event.src_path, dir=True)
        else:
            raise Exception(event)

    @pytest.mark.parametrize('input, expected, delay', [(case['input'], case['output'], case.get('delay')) for case in CASES])
    def test_event_observer(self, monkeypatch, tmpdir, input, expected, delay):
        og_input = tuple(input)
        def local_to_db(local, node, *, is_folder=False, check_is_folder=True):
            found = False
            for event in reversed(og_input):
                if str(tmpdir.join(getattr(event, 'dest_path', ''))) == str(local):
                    return local_to_db(tmpdir.join(event.src_path), None)

                if str(tmpdir.join(event.src_path)) == str(local):
                    found = event
                    if event.event_type == events.EVENT_TYPE_CREATED:
                        return False

            # Doesnt really matter, just needs to be truthy and have a sha256
            return found

        def sha256_from_event(event):
            for evt in og_input:
                if str(event.src_path) in (str(tmpdir.join(evt.src_path)), str(tmpdir.join(getattr(evt, 'dest_path', evt.src_path)))):
                    event.is_directory = evt.is_directory  # Hack to make tests pass on windows. Delete events are emitted as file deletes. Other code compensates for this
                    if evt.sha256:
                        return evt.sha256

            if event.event_type == events.EVENT_TYPE_DELETED:
                return None

            try:
                return utils.hash_file(Path(getattr(event, 'dest_path', event.src_path)))
            except (IsADirectoryError, PermissionError):
                return None

        monkeypatch.setattr('osfoffline.sync.local.utils.extract_node', lambda *args, **kwargs: None)
        monkeypatch.setattr('osfoffline.sync.local.utils.local_to_db', local_to_db)
        monkeypatch.setattr('osfoffline.sync.ext.watchdog.settings.EVENT_DEBOUNCE', 2)
        monkeypatch.setattr('osfoffline.sync.ext.watchdog.sha256_from_event', sha256_from_event)

        # De dup input events
        for event in tuple(input):
            for evt in tuple(input):
                if event is not evt and not isinstance(event, events.DirModifiedEvent) and event.event_type != events.EVENT_TYPE_CREATED and evt.event_type == event.event_type and evt.src_path.startswith(os.path.join(event.src_path, '')) and (event.event_type != events.EVENT_TYPE_MOVED or evt.dest_path.startswith(os.path.join(event.dest_path, ''))):
                    input.remove(evt)

        for event in reversed(input):
            path = tmpdir.ensure(event.src_path, dir=event.is_directory)
            if not event.is_directory:
                with path.open('wb+') as fobj:
                    fobj.write(os.urandom(50))

            if isinstance(event, (events.FileMovedEvent, events.DirMovedEvent)):
                tmpdir.ensure(event.dest_path, dir=event.is_directory).remove()

            if isinstance(event, (events.FileCreatedEvent, events.DirCreatedEvent)):
                path.remove()

        observer = TestSyncObserver(tmpdir.strpath, 1)
        # Clear cached instance of Observer
        del type(TestSyncObserver)._instances[TestSyncObserver]

        observer.start()
        assert observer.is_alive()

        # Wait until watchdog is actually reporting events
        retries = 0
        path = tmpdir.ensure('plstonotuse')
        with path.open('w') as fobj:
            while True:
                fobj.write('Testing...\n')
                fobj.flush()
                if observer.done.wait(3):
                    break
                retries += 1
                if retries > 4:
                    raise Exception('Could not start observer')

        observer.flush()
        observer.expected = 1
        observer._events = []
        observer.done.clear()

        path.remove()
        observer.done.wait(5)

        # Reset the observer to its inital state
        observer.flush()
        observer.expected = len(expected)
        observer._events = []
        observer.done.clear()

        for event in input:
            self.perform(tmpdir, event)
            if delay:
                time.sleep(delay)

        observer.done.wait(3)
        observer.stop()
        observer.flush()

        assert len(expected) == len(observer._events)

        for event, context in zip(expected, observer._events):
            assert CONTEXT_EVENT_MAP[type(event)] == type(context)
            assert str(tmpdir.join(event.src_path)) == str(context.local)
