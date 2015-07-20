from unittest import TestCase
from osfoffline.models import User, Node, File
import osfoffline.db as db
from tests.fixtures.factories import common
from appdirs import user_data_dir
import os
import threading
import shutil
from tests.fixtures.factories.factories import UserFactory, NodeFactory, FileFactory
from sqlite3 import IntegrityError


class TestModels(TestCase):
    def setUp(self):
        self.session = common.Session()

    def tearDown(self):
        self.session.rollback()
        self.session.query(User).delete()
        self.session.query(Node).delete()
        self.session.query(File).delete()
        common.Session.remove()

    def test_create_user(self):
        u = UserFactory()
        self.assertEqual([u], self.session.query(User).all())

    def test_delete_user(self):
        u = UserFactory()
        self.assertEqual([u],self.session.query(User).all())
        self.session.delete(u)
        self.assertEqual([], self.session.query(User).all())


    def test_delete_user_with_top_level_nodes(self):
        u = UserFactory()
        tp_node = NodeFactory()
        u.nodes.append(tp_node)
        self.assertEqual([tp_node], self.session.query(User).one().top_level_nodes)

        self.session.delete(u)
        #node should have been deleted as soon as user was deleted
        self.assertEqual([], self.session.query(Node).all())

    def test_delete_user_with_no_top_level_nodes(self):
        u = UserFactory()

        self.assertEqual([], self.session.query(User).one().top_level_nodes)

        self.session.delete(u)
        #node should have been deleted as soon as user was deleted
        self.assertEqual([], self.session.query(Node).all())



    def test_delete_users_files_and_nodes(self):
        u = UserFactory()
        node = NodeFactory(user=u)
        file = FileFactory(node=node,user=u )


        self.assertEqual([file], u.files)
        self.assertEqual([node], u.nodes)
        self.session.commit()

        self.session.delete(u)
        self.session.commit()

        self.assertEqual([], self.session.query(File).all())
        self.assertEqual([], self.session.query(Node).all())


    def test_get_users_top_level_nodes(self):
        u = UserFactory()
        tp_node = NodeFactory( user=u)
        node = NodeFactory( user=u, parent=tp_node)



        self.assertTrue(node in u.nodes)
        self.assertTrue(tp_node in u.nodes)
        self.assertEqual(len(u.nodes),2)
        self.assertEqual([tp_node], u.top_level_nodes)



    def test_delete_top_level_nodes(self):
        u = UserFactory()
        tp_node = NodeFactory( user=u)
        node = NodeFactory( user=u, parent=tp_node)
        tp_node2 = NodeFactory(user=u)

        self.assertEqual(len(u.nodes),3)
        self.assertTrue(node in u.nodes)
        self.assertTrue(tp_node in u.nodes)
        self.assertTrue(tp_node2 in u.nodes)

        self.assertEqual(len(u.top_level_nodes),2)
        self.assertTrue(tp_node in u.top_level_nodes)
        self.assertTrue(tp_node2 in u.top_level_nodes)

        self.assertEqual([node], tp_node.child_nodes)
        self.assertEqual([], tp_node2.child_nodes)


        # delete tp_node
        # need to flush to db before we can delete node
        self.session.flush()
        self.session.delete(tp_node)
        self.session.refresh(u)

        self.assertEqual([tp_node2], u.nodes)
        self.assertEqual([tp_node2], u.top_level_nodes)

        # delete node
        # self.assertWarns(SAWarning, self.session.delete, node)


        # delete tp_node2
        self.session.flush()
        self.session.delete(tp_node2)
        self.session.refresh(u)

        self.assertEqual([], u.nodes)
        self.assertEqual([], u.top_level_nodes)



    def test_delete_nodes_with_files(self):
        u = UserFactory()
        tp_node = NodeFactory(user=u)
        folder = FileFactory(user=u, node=tp_node)
        file = FileFactory(user=u, node=tp_node, parent=folder)

        # delete node
        self.session.flush()
        self.session.delete(tp_node)
        self.session.refresh(u)


        # check node doesnt exist
        self.assertEqual([], self.session.query(Node).all())
        self.assertEqual([], u.top_level_nodes)

        # check files dont exist
        self.assertEqual([], u.files)
        self.assertEqual([], self.session.query(File).all())


    def test_node_without_user(self):
        node = NodeFactory()
        with self.assertRaises(IntegrityError):
          self.session.flush()


    def test_node_without_parent(self):
        u = UserFactory()
        node = NodeFactory(user=u)
        self.assertTrue(node.top_level)

    def test_file_without_node(self):
        user = UserFactory()
        with self.assertRaises(IntegrityError):
            file = FileFactory(user=user)
            self.session.flush()

    def test_file_without_user(self):
        user = UserFactory()
        node = NodeFactory(user=user)
        with self.assertRaises(IntegrityError):
            FileFactory(node=node)
            self.session.flush()

    def test_file_without_parent(self):
        u = UserFactory()
        node = NodeFactory(user=u)
        file = FileFactory(user=u, node=node)
        self.assertFalse(file.has_parent)

"""
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