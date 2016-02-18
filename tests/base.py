import os
import shutil
import itertools

import pytest
import unittest

from osfoffline import settings
from osfoffline.database import models
from osfoffline.database import drop_db, Session

from tests.utils import (
    unique_file_name,
    unique_folder_name,
    unique_sha256,
    unique_guid,
    unique_id,
    unique_project_name,
)

def make_project_structure():
    return [
        {
            'name': unique_project_name(),
            'id': unique_guid(),
            'children': [],
            'files': [
                {
                    'name': unique_folder_name(),
                    'type': 'folder',
                    'id': unique_id(),
                    'children': [
                        {
                            'name': unique_file_name(),
                            'type': 'file',
                            'id': unique_id(),
                            'sha256': unique_sha256()
                        }
                    ]
                },
                {
                    'name': unique_folder_name(),
                    'type': 'folder',
                    'id': unique_id(),
                    'children': []
                }
            ]
        }
    ]

class OSFOTestBase(unittest.TestCase):

    PROJECT_STRUCTURE = None

    def _make_dummy_file(self, path):
        with open(path, 'w') as fp:
            fp.write('With gorilla gone, what will become of man?')

    def _ensure_file_structure(self, root, files):
        files = iter(files)
        while True:
            try:
                file_node = next(files)
            except StopIteration:
                break
            if file_node.get('parent'):
                file_node['rel_path'] = os.path.join(
                    file_node['parent']['rel_path'],
                    file_node['name']
                )
            else:
                file_node['rel_path'] = os.path.join(
                    root.relto(self.root_dir),
                    file_node['name']
                )
            if file_node['type'] == 'folder':
                self.root_dir.ensure_dir(
                    file_node['rel_path']
                )
            else:
                self._make_dummy_file(
                    os.path.join(
                        str(self.root_dir),
                        file_node['rel_path']
                    )
                )
            children = file_node.get('children', [])
            for child in children:
                child['parent'] = file_node
            files = itertools.chain(files, children)

    def _ensure_project_structure(self, project, parent):
        for child in project.get('children', []):
            child_dir = parent.mkdir(child['name'])
            child_osfstorage_dir = child_dir.mkdir(settings.OSF_STORAGE_FOLDER)
            self._ensure_file_structure(child_osfstorage_dir, child.get('files', []))
            child_components_dir = child_dir.mkdir(settings.COMPONENTS_FOLDER)
            for subchild in child.get('children', []):
                self._ensure_project_structure(subchild, child_components_dir)

    def _reset_database(self):
        drop_db()
        user = models.User(
            id='fake_user_id',
            full_name='fake full name',
            login='fake_username',
            oauth_token='fake_personal_access_token',
            folder=str(self.root_dir)
        )
        node = models.Node(
            id=self.PROJECT_STRUCTURE[0]['id'],
            title=self.PROJECT_STRUCTURE[0]['name'],
            sync=True,
            user_id = user.id
        )
        with Session() as session:
            session.add(user)
            session.add(node)
            session.commit()

    @pytest.fixture(scope='function', autouse=True)
    def initdir(self, request, tmpdir):
        self.PROJECT_STRUCTURE = self.PROJECT_STRUCTURE or make_project_structure()
        self.root_dir = tmpdir
        self._reset_database()
        # change to pytest-provided temporary directory
        tmpdir.chdir()
        # create test directory structure
        for project in self.PROJECT_STRUCTURE:
            project_dir = tmpdir.mkdir(
                project['name']
            )
            project['rel_path'] = project_dir.relto(tmpdir)
            project_osfstorage_dir = project_dir.mkdir(
                settings.OSF_STORAGE_FOLDER
            )
            project_osfstorage_dir.chdir()
            self._ensure_file_structure(
                project_osfstorage_dir,
                project['files']
            )
            if project.get('children'):
                project_components_dir = project_dir.mkdir(
                    settings.COMPONENTS_FOLDER
                )
                for child in project['children']:
                    self._ensure_project_structure(child, project_components_dir)
        tmpdir.chdir()
        def clean():
            shutil.rmtree(str(tmpdir))
        request.addfinalizer(clean)
