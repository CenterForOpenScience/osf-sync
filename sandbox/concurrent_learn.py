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

class User(Base):
     __tablename__ = 'user'

     id = Column(Integer, primary_key=True)
     fullname = Column(String)

     def __repr__(self):
       return "<User(fullname={})>".format(
                             self.fullname)

class Thread1(Thread):
    def __init__(self):
        super().__init__()
        url = 'sqlite:///{}'.format('/home/himanshu/OSF-Offline/sandbox/concurrent.db')
        #todo: figure out if this is safe or not. If not, how to make it safe?????
        engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        self.session = Session()


    def run(self):
        for i in range(100):
            u= User(fullname='user{}'.format(i))
            self.session.add(u)
            self.session.commit()
            print('added')
        print('done with t1')


class Thread2(Thread):
    def __init__(self):
        super().__init__()
        url = 'sqlite:///{}'.format('/home/himanshu/OSF-Offline/sandbox/concurrent.db')
        #todo: figure out if this is safe or not. If not, how to make it safe?????
        engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        self.session = Session()


    def run(self):
        for user in self.session.query(User):
            print('.')
            print(user.fullname)
        print('done with t2 part one')
        for i in range(100000):
            f = 3+3
        for user in self.session.query(User):
            print(user.fullname)
        print('done with t2 part two')
        tempuser = self.session.query(User).first()
        tempuser.fullname="a"
        self.session.add(tempuser)
        self.session.commit()
        print('done adding imanshu to db')
        himanshu = self.session.query(User).filter(User.fullname=='a').first()
        print(himanshu.fullname)

# if __name__=="__main__":
#     url = 'sqlite:///{}'.format('/home/himanshu/OSF-Offline/sandbox/concurrent.db')
#     engine = create_engine(url, echo=False)
#     Base.metadata.create_all(engine)
#
#     t1 = Thread1()
#     t2 = Thread2()
#     t2.start()
#     t1.start()
#     t1.join()
#     t2.join()



class BackgroundWorker(Thread):
    def __init__(self):
        super().__init__()
        self._keep_running = True
        self._waiting_coros = Queue()
        # self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.
        self.session = self.make_session()
        # asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        self._tasks = []

    def make_session(self):
        url = 'sqlite:///{}'.format('/home/himanshu/OSF-Offline/sandbox/concurrent.db')
        engine = create_engine(url, echo=False, poolclass=SingletonThreadPool)
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        Base.metadata.create_all(engine)
        return Session()


    def stop(self):
        self._keep_running = False
        self.join()


    def run(self):
        print('{}'.format(threading.current_thread()))
        self._loop = asyncio.new_event_loop()       # Implicit creation of the loop only happens in the main thread.
        asyncio.set_event_loop(self._loop)          # Since this is a child thread, we need to do it manually.
        self.limit_simultaneous_processes = asyncio.Semaphore(2)
        self._loop.run_until_complete(self.process_coros())


    def submit_coro(self, coro, callback=None):
        self._waiting_coros.put((coro, callback))

    @asyncio.coroutine
    def process_coros(self):
        while self._keep_running:
            try:
                while True:
                    # import pdb;pdb.set_trace()
                    print('{}'.format(threading.current_thread()))
                    coro, callback = self._waiting_coros.get_nowait()
                    task = asyncio.async(coro())
                    if callback:
                        task.add_done_callback(callback)
                    self._tasks.append(task)
            except Empty as e:
                print('done with all tasks')
            yield from asyncio.sleep(3)     # sleep so the other tasks can run

    #DB TASKS
    @asyncio.coroutine
    def create_user(self):
        print('create_user actually called.')
        user = User(fullname='as')
        self.session.add(user)
        self.session.commit()
        yield from asyncio.sleep(1)


background_worker = BackgroundWorker()


if __name__=="__main__":
    background_worker.submit_coro(background_worker.create_user, callback=lambda a: print('done with task.'))
    background_worker.start()
    print('hi')
    background_worker.stop()





