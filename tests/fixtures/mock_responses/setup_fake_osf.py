__author__ = 'himanshu'
from tests.utils.url_builder import *
import httpretty
from tests.fixtures.mock_responses.osf_api import (
    create_new_user,
    create_new_top_level_node,
    get_user, get_user_nodes,
    create_provider_folder,
    get_providers_for_node,
    create_new_folder,
    create_new_file,
    get_children_for_folder
)

def register_user_url(user):
    httpretty.register_uri(
        httpretty.GET,
        api_user_url(user.id),
        body=get_user,
        content_type="application/json"
    )


def register_user_nodes_url(user):

    httpretty.register_uri(
        httpretty.GET,
        api_user_nodes(user.id),
        body=get_user_nodes,
        content_type="application/json"
    )



def register_node_providers_url(node):
    httpretty.register_uri(
        httpretty.GET,
        api_node_files(node.id),
        body=get_providers_for_node,
        content_type="application/json"
    )

def register_folder_children_url(folder):

    httpretty.register_uri(
        httpretty.GET,
        api_file_children(folder.node.id, folder.path, folder.provider),
        body=get_children_for_folder,
        content_type="application/json"
    )


# def register_wb_urls():
#     httpretty.register_uri(
#         httpretty.POST,
#         wb_file_url(),
#         body=,
#         content_type="application/json"
#     )
#     httpretty.register_uri(
#         httpretty.GET,
#         api_file_children(folder.node.id, folder.path, folder.provider),
#         body=get_children_for_folder,
#         content_type="application/json"
#     )
#     httpretty.register_uri(
#         httpretty.GET,
#         api_file_children(folder.node.id, folder.path, folder.provider),
#         body=get_children_for_folder,
#         content_type="application/json"
#     )