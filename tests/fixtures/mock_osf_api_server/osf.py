from tests.fixtures.mock_osf_api_server.models import User, Node, File
from flask import Flask, jsonify, request, make_response
import json
from furl import furl
from decorator import decorator
from tests.fixtures.mock_osf_api_server.utils import (
    session,
    must_be_logged_in,
    save,
    get_user
)


app = Flask(__name__)


@app.route("/v2/users/", methods=['POST']) # create user
@app.route("/v2/users/<user_id>/", methods=['GET']) # get user
def user(user_id=None):
    if request.method == 'POST':

        fullname = request.form['fullname']
        user = User(fullname=fullname)
        save(user)
        session.refresh(user)
        return jsonify({
                'data': user.as_dict()
            })
    elif request.method =='GET':
        print(user_id)
        user = session.query(User).filter(User.id == user_id).one()
        return jsonify({
            'data': user.as_dict()
        })


@app.route("/v2/nodes/", methods=['POST']) # create node
@must_be_logged_in
def node():
    if request.method == 'POST':

        user = get_user()
        title = request.form['title']
        node = Node(title=title, user=user)
        session.refresh(user)
        save(node)

        provider = File(type=File.FOLDER, user=user, node=node)
        node.files.append(provider)
        save(node)
        session.refresh(node)
        return jsonify({
                'data': node.as_dict()
            })
    # elif request.method =='GET':
    #     user = get_user()
    #     node_id = request.form['id']
    #     node = session.query(Node).filter(user=user and id=)
    #     assert
    #     resp =  json.dumps({
    #         'data': user.as_dict()
    #     })


@app.route("/v2/users/<user_id>/nodes/", methods=['GET'])  # user's nodes
@must_be_logged_in
def user_nodes(user_id):
    if request.method=='GET':

        user = get_user()
        assert str(user_id) == str(user.id)
        users_nodes = session.query(Node).filter(Node.user == user).all()

        return jsonify({
            'data':[node.as_dict() for node in users_nodes]
        })


@app.route("/v2/nodes/<node_id>/files/<provider>/<file_id>", methods=['GET', 'DELETE'])  # node's files
@must_be_logged_in
def node_files(node_id, provider=None,file_id=None):
    if provider:
        assert file_id is not None

    if request.method=='GET':
        if provider is None:
            user = get_user()
            node = session.query(Node).filter(Node.user==user and Node.id==node_id).one()
            return jsonify({
                'data': [file_folder.as_dict() for file_folder in node.files]
            })
        else:
            file = session.query(File).filter(File.id==file_id and File.user==get_user()).one()
            return jsonify({
                'data': file.as_dict()
            })
    elif request.method=='DELETE':
        # deletes everything with given file id and given user.
        file = session.query(File).filter(File.id==file_id and File.user==get_user()).delete()
        #todo: unclear what to return in this case right now.
        return jsonify({'success':'true'})

@app.route("/v2/files/<file_id>", methods=['GET', 'PUT','PATCH'])  # files
@must_be_logged_in
def file_info(file_id):
    if request.method=='GET':
        user = get_user()
        file_folder = session.query(Node).filter(File.user==user and File.id==file_id).one()
        return jsonify({
            'data': [file_folder.as_dict()]
        })
    #todo: this code for put and patch files deals with file checkout. it does NOT match with what api does. understand and fix.
    elif request.method == 'PUT':
        file_folder = session.query(Node).filter(File.id==file_id).one()
        file_folder.checked_out = True
        save(file_folder)
    elif request.method == 'PATCH':
        file_folder = session.query(Node).filter(File.id==file_id).one()
        file_folder.checked_out = True
        save(file_folder)


@app.route("/v1/resources/<node_id>/providers/<provider>/<file_id>", methods=['GET','PUT'])  # waterbutler stuff for files
@must_be_logged_in
def resources(node_id, provider, file_id):
    if request.method=='GET': # download
        file = session.query(File).filter(File.id==file_id and File.user==get_user()).one()
        assert file.is_file
        #make it so that the returned content is actually downloadable.
        content = file.contents
        response = make_response(content)
        # Set the right header for the response
        response.headers["Content-Disposition"] = "attachment; filename={}".format(file.name)
        return response
    elif request.method == 'PUT': # upload new file, upload new folder, update existing file
        file_folder = session.query(File).filter(File.id==file_id and File.user==get_user()).one()
        if file_folder.is_folder: # upload new file, upload new folder
            parent = file_folder
            kind = request.args.get('kind','folder')
            new_file_folder = File(
                type=File.FILE if kind == 'file' else File.FOLDER,
                node=parent.node,
                user=parent.user,
                parent=parent,
                name=request.args.get('name'),
                provider=provider,
                content=request.get_data() if kind == 'file' else None
            )
            session.refresh(new_file_folder)
            return jsonify({
                'data': new_file_folder.as_dict()
            })
        else: # update existing file
            assert request.args.get('kind') == 'file'
            assert request.args.get('name') is not None

            # this creates new version of the file
            file_folder.content = request.get_data()
            file_folder.name = request.args.get('name')
            session.refresh(file_folder)
            return jsonify({
                'data': file_folder.as_dict()
            })
    elif request.method=='POST': # rename, move
        #todo: this part is a bit unclear. what  values can action take?
        file_folder = session.query(File).filter(File.id==file_id).one()
        if request.json['action'] == 'rename':
            file_folder.name = request.json['rename']
            save(file_folder)
            session.refresh(file_folder)
            return jsonify({
                'data': file_folder.as_dict()
            })
        elif request.json['action'] == 'move':
            new_parent_id = request.json['path'].split('/')[1]
            new_parent = session.query(File).filter(File.id == new_parent_id).one()
            file_folder.parent = new_parent

            if request.json['rename']:
                file_folder.name = request.json['rename']

            save(file_folder)
            session.refresh(file_folder)
            return jsonify({
                'data': file_folder.as_dict()
            })
    elif request.method=='DELETE':
        session.query(File).filter(File.id==file_id and File.user==get_user()).delete()
        #todo: unclear what to return in this case right now.
        return jsonify({'success':'true'})















# @app.route("/v2/nodes/<node_id>/downloads/<file_id>", methods=['GET'])  # download files
# @must_be_logged_in
# def node_files(node_id, file_id):
#     if request.method=='GET':
#         file = session.query(File).filter(File.id==file_id and File.user==get_user()).one()
#         assert file.is_file
#         #make it so that the returned content is actually downloadable.
#         content = file.contents
#         response = make_response(content)
#         # Set the right header for the response
#         response.headers["Content-Disposition"] = "attachment; filename={}".format(file.name)
#         return response








# @must_be_logged_in
# def create_node(request, uri, headers):
#     try:
#         user_id = user_id_from_request(request)
#         user = session.query(User).filter(User.id ==user_id).one()
#         title = request.parsed_body['title'][0]
#         node = Node(user=user, title=title)
#         save(node)
#         session.refresh(node)
#         provider = File(type=File.FOLDER, user=user, node=node)
#         node.files.append(provider)
#         save(node)
#         session.refresh(node)
#         resp = json.dumps({
#             'data':node.as_dict()
#         })
#         return (200, headers, resp)
#     except:
#         return (400, headers, 'cant get user nodes')
#
#
# @must_be_logged_in
# def get_user_nodes(request, uri, headers):
#     try:
#         user_id = furl(uri).path.segments[2]
#
#         user = session.query(User).filter(User.id ==user_id).one()
#
#         nodes = user.nodes
#         # return 200, headers, json.dumps({'data':'asd'})
#         resp = [node.as_dict() for node in nodes]
#         resp = json.dumps({
#             'data':resp
#         })
#         return (200, headers, resp)
#     except:
#         return (400, headers, 'cant get user nodes')
#
# def get_all_nodes(request, uri, headers):
#     try:
#
#         nodes = session.query(Node).all()
#         resp = [node.as_dict() for node in nodes]
#         resp = json.dumps({
#             'data':resp
#         })
#         return (200, headers, resp)
#     except:
#         return (400, headers, 'ERROR in getting all nodes')
#
# # @must_be_logged_in
# # def get_providers_for_node(request, uri, headers):
# #     try:
# #
# #         nid = furl(uri).path.segments[2]
# #
# #         node = session.query(Node).filter(Node.id == nid).one()
# #         print('hifahsidfadsf')
# #         resp = [provider.as_dict() for provider in node.providers]
# #
# #         resp = json.dumps({
# #             'data':resp
# #         })
# #         return (200, headers, resp)
# #     except:
# #         return (400, headers, 'cant get providers for node')
#
# @must_be_logged_in
# def get_node_children(request, uri, headers):
#     try:
#
#         nid = furl(uri).path.segments[2]
#         node = session.query(Node).filter(Node.id == nid).one()
#
#         resp = [child.as_dict() for child in node.child_nodes]
#         resp = json.dumps({
#             'data':resp
#         })
#         return (200, headers, resp)
#     except:
#         return (400, headers, 'cant get children for node')
#
#
#
# @must_be_logged_in
# def get_children_for_folder(request, uri, headers):
#     try:
#
#         folder_path = furl(uri).args['path']
#
#         nid = furl(uri).path.segments[2]
#
#         for file_folder in session.query(File):
#             if not file_folder.is_file:
#                 if file_folder.node.id == int(nid) and file_folder.path == folder_path:
#                     resp = [child.as_dict() for child in file_folder.files]
#                     resp = json.dumps({
#                         'data':resp
#                     })
#                     return (200, headers, resp)
#     except:
#         return (400, headers, 'cant get providers for node')
#
# @must_be_logged_in
# def create_folder(request, uri, headers):
#
#     data = furl(uri).args['path']
#
#     parts = data.split('/')
#     parent_path = parts[1] if len(parts)==3 else '/'
#     new_folder_name = parts[2] if len(parts)==3 else parts[1]
#
#     provider = furl(uri).args['provider']
#     nid = furl(uri).args['nid']
#     return 200, headers, json.dumps({
#         'data':'ahahah'
#     })
#     parent = session.query(File).filter(File.is_folder and File.node_id==nid and File.path==parent_path).one()
#     assert parent.node.id == nid
#
#     new_folder = File(type=File.FOLDER, node=parent.node, user=parent.user,
#                       parent=parent, name=new_folder_name, provider=provider)
#     save(parent)
#     save(new_folder)
#     resp = json.dumps({
#         'data':new_folder.as_dict()
#     })
#     return (200, headers, resp)
#
#
#
# @must_be_logged_in
# def create_file(request, uri, headers):
#     folder_path = furl(uri).args['path']
#     # folder_name = folder_path.split('/')[1]
#     # provider_name = furl(uri).args['path']
#     nid = furl(uri).args['nid']
#     provider = session.query(File).filter(File.parent == None and File.node_id==nid).one()
#     new_file = create_new_file(provider)
#     resp = json.dumps({
#         'data':new_file.as_dict()
#     })
#     return (200, headers, resp)
#
# # @must_be_logged_in
# # def download_file(request, uri, headers):
#
#


