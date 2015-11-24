import asyncio

from osfoffline.database_manager.db import session
from osfoffline.database_manager import models
from osfoffline.sync.database import DatabaseSync
from osfoffline.tasks.queue import TaskQueue
# from osfoffline.client.osf import OSFClient


try:
    asyncio.ensure_future
except AttributeError:
    asyncio.ensure_future = asyncio.async


    # def __init__(self, observer, user, loop=None):
    #     self.user = user
    #     self.observer = observer
    #     self.loop = loop or asyncio.get_event_loop()
    #     self.osf_query = OSFQuery(self.loop, self.user.oauth_token)
    #     self.osf_folder = self.user.osf_local_folder_path
    #
    #     if not os.path.isdir(self.osf_folder):
    #         raise FolderNotInFileSystem
    #
    #     self.osf_path = ProperPath(self.osf_folder, True)
    #
    # def sync_db(self):


@asyncio.coroutine
def main():
    # perform initial sync of db
    # loop = asyncio.get_event_loop()

    root_dir = '/Users/michael/Desktop/OSF'
    user = session.query(models.User).one()

    queue = TaskQueue()
    queue_job = asyncio.ensure_future(queue.start())
    queue_job.add_done_callback(handle_exception)

    database_sync = DatabaseSync(queue, user)
    yield from database_sync.check()

    # client = OSFClient(user.oauth_token)
    # node = yield from client.get_node('9m5tc')
    # folder = yield from node.get_storage('osfstorage')
    # children = yield from folder[0].get_children()
    # i = 0
    # query = OSFQuery(asyncio.get_event_loop(), user)
    # query.list_to

    # local_sync = sync.LocalSync(queue)
    # local_sync_job = asyncio.ensure_future(local_sync.start())
    # local_sync_job.add_done_callback(handle_exception)
    #
    # remote_sync = sync.RemoteSync(queue)
    # remote_sync_job = asyncio.ensure_future(remote_sync.start())
    # remote_sync_job.add_done_callback(handle_exception)

    # while True:
    #     yield from asyncio.sleep(1)
    #     yield from task_queue.put(events.BaseEvent())

    # loop.run_until_complete()


    # self.tasks = asyncio.ensure_future(self.process_queue())
    # self.poll_job = asyncio.ensure_future(self.check_osf(remote_user))


    # remote_user = self._loop.run_until_complete(self.get_remote_user())
    #
    # self.queue = JoinableQueue(maxsize=15)
    #
    # self.process_job = asyncio.ensure_future(self.process_queue())
    # self.poll_job = asyncio.ensure_future(self.check_osf(remote_user))
    #
    # self.poll_job.add_done_callback(self.handle_exception)
    # self.process_job.add_done_callback(self.handle_exception)
    #
    # return True





def handle_exception(self, future):
    i = 0
    pass
    # # Note: The actual futures never exit, if they do an exception is raised
    # try:
    #     raise future.exception()
    # except (aiohttp.ClientError, asyncio.TimeoutError):
    #     logger.error('Unable to connect to the internet')
    #     AlertHandler.warn('Unable to connection to OSF, we\'ll try again later.')
    # except asyncio.CancelledError:
    #     # Cancellations just mean this thread is exiting
    #     return
    #
    # # Make sure all our jobs are cancelled
    # if future == self.poll_job:
    #     self.process_job.cancel()
    # else:
    #     self.poll_job.cancel()
    #
    # logger.info('Restarting polling in 5 seconds')
    # # Finally restart our watcher thread in 5 seconds
    # self._loop.call_later(5, self.start)


if __name__ == '__main__':
    asyncio.get_event_loop().set_debug(True)
    asyncio.get_event_loop().run_until_complete(main())