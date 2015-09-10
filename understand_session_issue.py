import os

#clear db
try:
    os.remove('/Users/himanshu/Library/Application Support/osf-offline/osf.db')
except Exception as e:
    print(e)

from osfoffline.database_manager.models import User, Node, File
from osfoffline.database_manager.db import session
from osfoffline.utils.path import ProperPath




#SETUP
osf_path = '/home/himanshu/Desktop/OSF'
user = User(full_name='hi', osf_local_folder_path=osf_path)
node = Node(title='nodeme', user=user)
user.nodes.append(node)
top_file = File(name='f1', user=user, node=node, type=File.FOLDER) # parent=None
inner_file = File(name='f2', user=user, node=node, parent=top_file, type=File.FILE)
new_parent_item = Node(title='other', user=user)
session.add_all([user, node, top_file, inner_file])
session.commit()
def get_item_by_path(path):
    for node in session.query(Node):
        if ProperPath(node.path, True) == path:
            return node
    for file_folder in session.query(File):
        file_path = ProperPath(file_folder.path, file_folder.is_folder)
        if file_path == path:
            return file_folder
    raise Exception
def get_parent_item_by_path(path):
    parent_path = path.parent
    return get_item_by_path(parent_path)


#DONE WITH SETUP
import ipdb;ipdb.set_trace()
child_path=ProperPath(os.path.join(osf_path, 'nodeme','f1','f2'),False)
child = get_item_by_path(child_path)
# top = get_parent_item_by_path(child_path)

child.parent =   None
assert ('f2',) in session.query(File.name).all()
if ('f2',) in session.query(File.name).all():
    print('ok')
session.add(child)
session.commit()

assert ('f2',) in session.query(File.name).all()
if ('f2',) in session.query(File.name).all():
    print('ok')


