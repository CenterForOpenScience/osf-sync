__author__ = 'himanshu'
import asyncio
import os
from osf_event_handler import OSFEventHandler
from watchdog.events import (
    DirDeletedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileCreatedEvent,
    DirCreatedEvent,
    LoggingFileSystemEventHandler
)
from watchdog.observers import Observer
from models import setup_db, User, Node, File, get_session, Base



def get_children(item):
    if item is None:
        return []
    if isinstance(item, File):
        return item.files
    elif isinstance(item, Node):
        return item.components + item.top_level_file_folders
    elif isinstance(item, User):
        return item.projects
    else:
        return os.listdir(get_path(item))

def get_path(item):
    if isinstance(item, User):
        return item.osf_path
    elif isinstance(item, Base):
        return item.path
    else:
        return os.path.join(osf_folder, item)

def represent_same_values(children, i):
    if i+1 < len(children):
        return os.path.samefile(
            get_path(children[i]),
            get_path(children[i+1])
        )
    else:
        return False

def make_local_db_tuple_list(local, db):
    assert local or db
    if local and db:
        assert get_path(local) == get_path(db)
    out=[]
    children = get_children(local) + get_children(db)
    children = sorted(children, key=get_path)
    print(children)
    i = 0
    while i < len(children):
        if represent_same_values(children,i):
            if isinstance(children[i], str):
                out.append( (children[i], children[i+1]) )
            else:
                out.append( (children[i+1], children[i]) )
            i += 1
        elif isinstance(children[i], Base):
            out.append( (None,children[i]) )
        else:
            out.append( (children[i],None) )
            print(out)
        i += 1

    for local, db in out:
        if local is not None and db is not None:
            assert get_path(local) == get_path(db)
        elif local is not None:
            assert db is None
            assert isinstance(local, str)
        elif db is not None:
            assert isinstance(db, Base)
        else:
            assert False
    return out


def determine_new_events(absolute_osf_dir_path, observer, user):

    local_db_tuple_list = make_local_db_tuple_list(absolute_osf_dir_path, user)
    for local, db in local_db_tuple_list:
        _determine_new_events(local, db, observer)   #local.path = /home/himanshu/OSF-Offline/dumbdir/OSF/p1/


def _determine_new_events(local, db, observer):
    assert local or db # a and b cannot both be none.
    if (local is not None) and (db is not None):
        assert get_path(local) == get_path(db)
        if isinstance(db, File) and db.type == File.FILE and hash(local) != hash(db): # hash!!!!!
            event = FileModifiedEvent(local.path)  # create changed event
        # folder modified event should not happen.
    elif local is None:
        db_path = get_path(db)
        if isinstance(db, File) and db.type == File.FILE:
            event = FileDeletedEvent(db_path)  # delete event for file
        else:
            event = DirDeletedEvent(db_path)
    elif db is None:
        local_path = get_path(local)
        if isinstance(db, File) and db.type == File.FILE:
            event = FileCreatedEvent(local_path)  # delete event for file
        else:
            event = DirCreatedEvent(local_path)

    if event:
        print(event.key)
        # event_queue = observer._event_queue
        # event_queue.put(event)
        # observer.dispatch_events(event_queue, observer._timeout)
        emitter = next(iter(observer.emitters))
        emitter.queue_event(event)
        # observer.emitters[0].queue_event(event)

    local_db_tuple_list = make_local_db_tuple_list(local, db)
    for local, db in local_db_tuple_list:
        _determine_new_events(local, db)

# observer = Observer()  # create observer. watched for events on files.

    # def stop_observing_osf_folder(self):
    #     self.observer.stop()
    #     self.observer.join()

# if __name__=='__main__':
#
#     setup_db('/home/himanshu/OSF-Offline/osfoffline/sandbox/db_folder/')
#     session = get_session()
#     osf_folder = '/home/himanshu/OSF-Offline/osfoffline/sandbox/dumbdir/OSF/'
#     user = User(osf_path= osf_folder)
#     session.add(user)
#     session.commit()
#
#     loop = asyncio.get_event_loop()
#
#     event_handler = OSFEventHandler(osf_folder, '','',loop)
#     observer.schedule(event_handler, osf_folder, recursive=True)
#
#
#     determine_new_events(user.osf_path)
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