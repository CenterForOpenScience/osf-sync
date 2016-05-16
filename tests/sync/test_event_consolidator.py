import pytest

from watchdog import events

from osfoffline.utils.log import start_logging
from osfoffline.sync.utils import EventConsolidator

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


def Event(type_, *src):
    assert len(src) < 3
    if len(src) > 1:
        assert src[0].endswith('/') == src[1].endswith('/')
    return _map[(type_, src[0].endswith('/'))](*(x.rstrip('/') for x in src))


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
        Event('move', '/parent/file.txt', '/george/file.txt'),
        Event('move', '/parent/child/file.txt', '/george/child/file.txt'),
        Event('move', '/parent/child/grandchild/file.txt', '/george/child/grandchild/file.txt'),
    ],
    'output': [
        Event('move', '/parent/child/grandchild/file.txt', '/george/child/grandchild/file.txt'),
        Event('move', '/parent/child/file.txt', '/george/child/file.txt'),
        Event('move', '/parent/file.txt', '/george/file.txt'),
    ]
}, {
    'input': [
        Event('delete', '/parent/file.txt'),
        Event('delete', '/parent/child/file.txt'),
        Event('delete', '/parent/child/grandchild/file.txt')
    ],
    'output': [
        Event('delete', '/parent/child/grandchild/file.txt'),
        Event('delete', '/parent/child/file.txt'),
        Event('delete', '/parent/file.txt'),
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

######## Weird cases Word/Vim/Tempfiles ############################
    'input': [
        Event('create', '/~WRL0001.tmp'),
        Event('modify', '/~WRL0001.tmp'),
        Event('move', '/file.docx', '/~WRL0005.tmp'),
        Event('move', '/~WRL0001.tmp', '/file.docx'),
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
    # 'input': [
    #     Event('move', '/file.docx', '/~WRL0005.tmp'),
    # ],
    # 'output': [Event('modify', '/file.docx')],
# }, {
    # 'input': [
    #     Event('move', '/~WRL0005.tmp', '/file.docx'),
    # ],
    # 'output': [Event('create', '/file.docx')],
# }, {
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
        Event('move', '/folder/donut.txt', '/other_folder/bagel.txt'),
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

# }, {
#     'input': [
#         Event('delete', '/donut.txt', sha=123)],
#         Event('create', '/bagel.txt', sha=123)],
#     ],
#     'output': [Event('move', '/bagel.txt', sha=123)]

# }, {
#     'input': [
#         Event('move', '/file1', '/file2')],
#         Event('delete', '/file1')],
#     ],
    # 'output': [Event('move', '/file1', '/file2')],
# }, {
#     'input': [
#         Event('delete', '/file2')],
#         Event('move', '/file1', '/file2')],
#     ],
    # 'output': [Event('modify', '/file2')],
# }, {

}]


class TestEventConsolidator:

    @pytest.mark.parametrize('input, expected', [(case['input'], case['output']) for case in CASES])
    def test_event_consolidator(self, input, expected):
        consolidator = EventConsolidator()
        for event in input:
            consolidator.push(event)
        assert list(consolidator.events) == list(expected)
