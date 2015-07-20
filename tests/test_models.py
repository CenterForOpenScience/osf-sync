from unittest import TestCase
from osfoffline.models import User, Node, File, get_session, setup_db, Session
from appdirs import user_data_dir
import os
import threading
import shutil
from tests.fixtures.factories.factories import UserFactory

class TestDBSetup(TestCase):
    def setUp(self):
        self.db_dir = user_data_dir(appname='test-app-name', appauthor='test-app-author')
        # creates a new db each time
        setup_db(self.db_dir)

        self.db_path = os.path.join(self.db_dir, 'osf.db')

        def session_work(input_session=None):
            # get session
            session = input_session if input_session else get_session()

            # add to db
            session.add(User())
            session.add(Node())
            session.add(File())
            session.commit()

            # query from db
            user = session.query(User).all()[0]
            node = session.query(Node).all()[0]
            file = session.query(File).all()[0]

            # remove from db
            session.delete(user)
            session.delete(node)
            session.delete(file)
            session.commit()

            # query again
            session.query(User).all()
            session.query(Node).all()
            session.query(File).all()

        self.session_work = session_work

    def tearDown(self):
        shutil.rmtree(self.db_dir)

    def test_setup_db_exists(self):
        self.assertTrue(os.path.isfile(self.db_path))

    # def test_db_encrypted(self):
    #     self.fail()

    def test_all_models_exist(self):
        self.session_work()

    # def test_same_session_in_multiple_threads(self):
    #     t1 = threading.Thread(target=self.session_work)
    #     t2 = threading.Thread(target=self.session_work)
    #     t3 = threading.Thread(target=self.session_work)
    #
    #     t1.start()
    #     t2.start()
    #     t3.start()
    #
    #     t1.join()
    #     t2.join()
    #     t3.join()


    # def test_multiple_sessions_in_single_thread(self):
    #     session1 = get_session()
    #     session2 = get_session()
    #     session3 = get_session()
    #     self.session_work(session1)
    #     self.session_work(session2)
    #     self.session_work(session3)

    # def test_multiple_sessions_in_multiple_thread(self):
    #     t1 = threading.Thread(target=self.session_work, args=[get_session()])
    #     t2 = threading.Thread(target=self.session_work, args=[get_session()])
    #     t3 = threading.Thread(target=self.session_work, args=[get_session()])
    #
    #     t1.start()
    #     t2.start()
    #     t3.start()
    #
    #     t1.join()
    #     t2.join()
    #     t3.join()



from .fixtures.factories import common


class TestModels(TestCase):
    def setUp(self):

        self.db_dir = user_data_dir(appname='test-app-name', appauthor='test-app-author')
        self.db_path = os.path.join(self.db_dir, 'osf.db')
        self.osf_folder_path = os.path.join(self.db_dir, "OSF")

        # creates a new db each time
        setup_db(self.db_dir)

        # self.user = User(
        #     full_name="test user",
        #     osf_login="test@email.com",
        #     osf_password="fakepass",
        #     osf_local_folder_path=self.osf_folder_path,
        #     oauth_token="faketoken",
        #     osf_id="fakeid",
        #     logged_in=False,
        # )
        # self.project0 = Node(
        #     title="title",
        #     category = Node.PROJECT,
        #     osf_id = "nodeid",
        # )
        # self.component0 = Node(
        #     title="title",
        #     category = Node.PROJECT,
        #     osf_id = "nodeid",
        # )
        self.session = get_session()

    def tearDown(self):
        self.session.rollback()
        # Session.remove()

    def test_create_user(self):
        u = UserFactory()
        self.assertEqual([u], self.session.query(User).all())

"""
    def test_delete_user(self):
        self.fail()

    def test_delete_user_with_top_level_nodes(self):
        self.fail()

    def test_delete_user_with_no_top_level_nodes(self):
        self.fail()

    def test_delete_user_with_files_no_nodes(self):
        self.fail()

    def test_delete_users_files_and_nodes(self):
        self.fail()

    def test_delete_nodes(self):
        self.fail()

    def test_delete_nodes_with_files(self):
        self.fail()

    def test_delete_files(self):
        self.fail()

class TestModelPath(TestCase):
    def setUp(self):
        self.db_dir = user_data_dir(appname='test-app-name', appauthor='test-app-author')
        setup_db(self.db_dir)
        self.session = get_session()
        self.db_path = os.path.join(self.db_dir, 'osf.db')
        self.osf_folder_path = os.path.join(self.db_dir, "OSF")

    def tearDown(self):
        self.session.rollback()


    def test_path_for_user(self):
        user = UserFactory()

    def test_path_for_node(self):
        self.fail()

    def test_file_path(self):
        self.fail()

    def test_node_path_when_file_deleted(self):
        self.fail()

    def test_node_path_when_file_added(self):
        self.fail()

    def test_node_path_without_user(self):
        self.fail()
"""