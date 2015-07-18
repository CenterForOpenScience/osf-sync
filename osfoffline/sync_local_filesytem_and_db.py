__author__ = 'himanshu'
import os
import hashlib
from watchdog.events import (
    DirDeletedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileCreatedEvent,
    DirCreatedEvent,
)
from models import setup_db, User, Node, File, get_session, Base
from path import ProperPath
from watchdog.observers import Observer
from osf_event_handler import OSFEventHandler
import asyncio


class LocalDBSync(object):
    def __init__(self, absolute_osf_dir_path, observer, user):
        assert isinstance(observer, Observer)
        assert isinstance(user, User)
        assert os.path.isdir(absolute_osf_dir_path)

        self.osf_path = ProperPath(absolute_osf_dir_path, True)
        self.observer = observer
        self.user = user

    def emit_new_events(self):
        local_db_tuple_list = self._make_local_db_tuple_list(self.osf_path, self.user)
        for local, db in local_db_tuple_list:
            self._emit_new_events(local, db)

    def _make_local_db_tuple_list(self, local, db):
        # assertions
        assert local or db
        if local and db:
            assert self._get_proper_path(local) == self._get_proper_path(db)
        # checks
        if local is None and db is None:
            raise ValueError
        if local and db and self._get_proper_path(local) != self._get_proper_path(db):
            raise ValueError

        out = []
        children = self._get_children(local) + self._get_children(db)
        children = sorted(children, key=lambda c: self._get_proper_path(c).full_path)

        i = 0
        while i < len(children):
            if self._represent_same_values(children, i):
                if isinstance(children[i], Base):
                    out.append(tuple(children[i+1], children[i]))
                else:
                    out.append(tuple(children[i], children[i+1]))
                # add an extra 1 because skipping next value
                i += 1
            elif isinstance(children[i], Base):
                out.append(tuple(None,children[i]))
            else:
                out.append(tuple(children[i],None))
            i += 1

        # assertions
        for local, db in out:
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

        return out

    def _get_children(self, item):
        if item is None:
            return []
        # db
        if isinstance(item, File):
            return item.files
        elif isinstance(item, Node):
            return item.components + item.top_level_file_folders
        elif isinstance(item, User):
            return item.projects
        # local
        elif os.path.isfile(item.full_path):
            return []
        else:
            children = []
            for child in os.listdir(item.full_path):
                children.append(os.path.join(item.full_path, child))
            return children

    def _get_proper_path(self, item):
        if isinstance(item, User):
            return ProperPath(item.osf_local_folder_path, True)
        elif isinstance(item, File) and item.type == File.FILE:
            return ProperPath(item.path, False)
        elif isinstance(item, Base):
            return ProperPath(item.path, True)
        elif isinstance(item, ProperPath):
            absolute = os.path.join(self.osf_path.full_path, item.full_path)
            return ProperPath(absolute, os.path.isdir(absolute))
        else:
            raise TypeError('somehow passed type {} into LocalDBSync._get_proper_path'.format(type(item)))

    def _represent_same_values(self, children, i):
        if i+1 < len(children):
            return self._get_proper_path(children[i]) == self._get_proper_path(children[i+1])
        else:
            return False

    def _make_hash(self, local):
        assert isinstance(local, ProperPath)

        m = hashlib.md5()
        with open(local.full_path, "rb") as f:
            while True:
                buf = f.read(2048)
                if not buf:
                    break
                m.update(buf)
        return m.hexdigest()

    def _determine_event_type(self, local, db):
        assert local or db  #a and b cannot both be none.
        event = None
        if local and db:
            assert self._get_proper_path(local) == self._get_proper_path(db)
            # todo: implement hash properly in db.
            if isinstance(db, File) and db.type == File.FILE and self._make_hash(local) != db.hash:
                event = FileModifiedEvent(self._get_proper_path(local).full_path)  # create changed event
            # folder modified event should not happen.determine_new_events
        elif local is None:
            db_path = self._get_proper_path(db).full_path
            if isinstance(db, File) and db.type == File.FILE:
                event = FileDeletedEvent(db_path)  # delete event for file
            else:
                event = DirDeletedEvent(db_path)
        elif db is None:
            local_path = self._get_proper_path(local)
            if local_path.is_dir:
                event = FileCreatedEvent(local_path.full_path)
            else:
                event = DirCreatedEvent(local_path.full_path)

        return event

    def _emit_new_events(self, local, db):
        assert local or db
        event = self._determine_event_type(local, db)
        if event:
            # print(event.key)

            # event_queue = observer._event_queue
            # event_queue.put(event)
            # observer.dispatch_events(event_queue, observer._timeout)
            emitter = next(iter(self.observer.emitters))
            emitter.queue_event(event)
            # observer.emitters[0].queue_event(event)
        local_db_tuple_list = self._make_local_db_tuple_list(local, db)
        for local, db in local_db_tuple_list:
            self._emit_new_events(local, db)

# observer = Observer()  # create observer. watched for events on files.

# if __name__=='__main__':
#
#     setup_db('home/himanshu/.local/share/OSF Offline')
#     session = get_session()
#     osf_folder = '/home/himanshu/OSF-Offline/osfoffline/sandbox/dumbdir/OSF/'
#     user = User(osf_path= osf_folder)
#     session.add(user)
#     session.commit()
#     observer = Observer()
#
#     loop = asyncio.get_event_loop()
#
#     event_handler = OSFEventHandler(osf_folder, '','',loop)
#     observer.schedule(event_handler, osf_folder, recursive=True)
#
#
#     determine_new_events(user.osf_path, observer, user)
#     observer.start()
#     loop.run_forever()





"""
PLAN:


1) we will do the same match up the local filesystem with whats in the db in a [(local, db)]
2) get_id in this case will just be path. local.path, os.path.fullpath.
3) local: file/folder full path,
   db:
3) can create new event Event(. . .) then you can use observer.queue_event(event)
    will have to research how the Event is created to make it match what filesystem does.


NOTE: os.walk will give you local file system. can compare to db. BUT, this doesnt tell you if something exists in db and not in filesystem. THUS DONT DO THIS.
NOTE: local is going to be path because thats all you need for folders.
NOTE: when CHECKING, you check to see if db item is a file. If file, then you check to see if different from what db has using YOU CAN ACTUALLY USE HASH IN THIS CASE!!!!!!!!!!

ISSUES:
1)
2)

"""