__author__ = 'himanshu'

import os
from models import setup_db, User, Node, File, get_session, Base
from watchdog.events import (
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    DirCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileCreatedEvent
)
def on_restart():
    update_db()




def get_children(item):
    if isinstance(item, File):
        return item.files
    elif isinstance(item, Node):
        return item.components + item.top_level_file_folders
    elif isinstance(item, User):
        return item.projects
    else:
        return os.listdir(item)

def get_path(item):
    if isinstance(item, Base):
        return item.path
    else:
        return item

def make_local_db_tuple(path):
    local = get local from path or None
    db = get db from path or None

def make_local_db_tuple_list(local, db):
    out=[]
    children = get_children(local) + get_children(db)
    children = sorted(children, key=get_path)
    i = 0
    while i < len(children):
        if children[i].path == children[i+1].path:
            if children[i] is local:
                out = out.append(children[i], children[i+1])
            else:
                out = out.append(children[i+1], children[i])
            i += 1
        elif children[i] is local:
            out = out.append(children[i], None)
        else:
            out = out.append(None,children[i])
        i +=1
    return out


def determine_new_events(absolute_osf_dir_path):
    local_db_tuple_list = make_local_db_tuple_list(absolute_osf_dir_path, user)
    for local, db in local_db_tuple_list:
        _determine_new_events(local, db)   #local.path = /home/himanshu/OSF-Offline/dumbdir/OSF/p1/


def _determine_new_events(local, db):
    assert local is not None or db is not None # a and b cannot both be none.
    if local is not None and db is not None:
        assert local.path == db.path
        if isinstance(db,File) and db.type == File.FILE and hash(local) != hash(db): # hash!!!!!
            event =create changed event

    if local is None:
        event = delete event

    if db is None:
        event = create event


    if event:
        emit (event)
    local_db_tuple_list = make_local_db_tuple_list (local, db)
    for local, db in local_db_tuple_list:
        _determine_new_events(local, db)


if __name__=='__main__':
    setup_db('home/himanshu/OSF-Offline/sandbox/db_folder/')
    session = get_session()
    user = User(osf_path= '/home/himanshu/OSF-Offline/dumbdir/')
    # should add projects/components/files/folders in here to compare paths.
    determine_new_events(user.osf_path)



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