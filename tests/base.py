import os
import shutil
import itertools

import pytest
import unittest

from osfoffline import settings

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
            'children': [
                {
                    unique_project_name(): {
                        'id': unique_guid()
                    }
                }
            ],
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
                }
            ]
        }
    ]

class OSFOTestBase(unittest.TestCase):

    PROJECT_STRUCTURE = None

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
                    os.path.sep,
                    file_node['name']
                )
            root.ensure(
                file_node['rel_path'],
                dir=(file_node['type'] == 'folder')
            )
            files = itertools.chain(files, file_node.get('children', []))

    def _ensure_project_structure(self, project, parent):
        for child in project.get('children', []):
            child_dir = parent.mkdir(child['name'])
            child_osfstorage_dir = child_dir.mkdir(settings.OSF_STORAGE_FOLDER)
            self._ensure_file_structure(child_osfstorage_dir, child.get('files', []))
            child_components_dir = child_dir.mkdir(settings.COMPONENTS_FOLDER)
            for subchild in child.get('children', []):
                self._ensure_project_structure(subchild, child_components_dir)

    @pytest.fixture(autouse=True)
    def initdir(self, request, tmpdir):
        self.PROJECT_STRUCTURE = self.PROJECT_STRUCTURE or make_project_structure()
        self.root_dir = str(tmpdir)
        # change to pytest-provided temporary directory
        tmpdir.chdir()
        # create test directory structure
        for project in self.PROJECT_STRUCTURE:
            project_dir = tmpdir.mkdir(
                project['name']
            )
            project['rel_path'] = str(project_dir)
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
