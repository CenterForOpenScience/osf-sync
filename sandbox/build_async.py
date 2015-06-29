import logging
import asyncio
from watchdog.observers import Observer
import threading
__author__ = 'himanshu'
from threading import Thread
# from models import User, Node, File, create_engine, sessionmaker, get_session, Base
from sqlalchemy.orm import scoped_session
from sqlalchemy.pool import SingletonThreadPool
__author__ = 'himanshu'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session
from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
# from sqlalchemy_mptt.mixins import BaseNestedSets
import asyncio
import os
from queue import Queue, Empty
import threading
Base = declarative_base()
import requests
class User(Base):
     __tablename__ = 'user'

     id = Column(Integer, primary_key=True)
     fullname = Column(String)

     def __repr__(self):
       return "<User(fullname={})>".format(
                             self.fullname)

EVENT_TYPE_MOVED = 'moved'
EVENT_TYPE_DELETED = 'deleted'
EVENT_TYPE_CREATED = 'created'
EVENT_TYPE_MODIFIED = 'modified'

class AIOEventHandler(object):
    """An asyncio-compatible event handler."""

    def __init__(self, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self.num_user = 0
        print('inside aioenventhandler loop is {}'.format(self._loop))



    @asyncio.coroutine
    def on_any_event(self, event):
        # print(event)
        session = get_session()
        for user in session.query(User):
            print(user.fullname)
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_moved(self, event):
        print('moved')
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_created(self, event):
        print('created')
        session = get_session()
        user = User(fullname='user{}'.format(self.num_user))
        session.add(user)
        session.commit()
        self.num_user += 1
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_deleted(self, event):
        print('delted')
        yield from asyncio.sleep(1)

    @asyncio.coroutine
    def on_modified(self, event):
        print('modified')
        yield from asyncio.sleep(1)

    def dispatch(self, event):
        _method_map = {
            EVENT_TYPE_MODIFIED: self.on_modified,
            EVENT_TYPE_MOVED: self.on_moved,
            EVENT_TYPE_CREATED: self.on_created,
            EVENT_TYPE_DELETED: self.on_deleted,
        }
        handlers = [self.on_any_event, _method_map[event.event_type]]
        for handler in handlers:

            self._loop.call_soon_threadsafe(
                asyncio.async,
                handler(event)
            )


class AIOWatchdog(object):

    def __init__(self, path='.', recursive=True, event_handler=None):
        self._observer = Observer()
        evh = event_handler or AIOEventHandler()
        self._observer.schedule(evh, path, recursive)

    def start(self):
        print('starting watchdog')
        self._observer.start()

    def stop(self):
        self._observer.stop()
        self._observer.join()
        print('stopped watchdog')

# @asyncio.coroutine
# def run_watchdog():
#     myeventhandler = AIOEventHandler(loop=loop)
#     watch = AIOWatchdog('/home/himanshu/OSF-Offline/sandbox/dumbdir/', event_handler=)
#     watch.start()
#     for _ in range(20):
#         yield from asyncio.sleep(1)
#     watch.stop()

Session = None
def make_session():
    url = 'sqlite:///{}'.format('/home/himanshu/OSF-Offline/sandbox/concurrent.db')
    engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
    session_factory = sessionmaker(bind=engine)
    global Session
    Session = scoped_session(session_factory)
    Base.metadata.create_all(engine)

def get_session():
    return Session()


def poll():
    print('polling the api')
    session = get_session()
    resp = requests.get('http://www.google.com')
    user = User(fullname=resp.content[:4])
    session.add(user)
    session.commit()
    print('----poll start--------')
    for user in session.query(User):
        print(user.fullname)
    print('----poll end--------')
    asyncio.get_event_loop().call_later(3, poll)



if __name__=="__main__":
    # logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    make_session()
    session = get_session()
    # print(loop)
    OSFFileWatcher = AIOEventHandler(loop=loop)
    # loop.set_debug(True)
    # run_watchdog()
    watchdog = AIOWatchdog(path='/home/himanshu/OSF-Offline/sandbox/dumbdir/', event_handler=OSFFileWatcher)
    watchdog.start()
    loop.call_later(3, poll)
    # loop.run_forever()
    loop.run_forever()
    # print('haha, this printed.')


