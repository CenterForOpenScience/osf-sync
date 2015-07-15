__author__ = 'himanshu'
import os

def normalize_path(path, is_dir):
    normalized_path = path
    # if path.endswith(os.sep) and is_dir:
    #     pass
    # elif path.endswith(os.sep) and not is_dir:
    #     normalized_path = path[0:-1* len(os.sep)]  # remove seperator
    # elif not path.endswith(os.sep) and is_dir:
    #     normalized_path = os.path.join(path, os.sep)  # add seperator
    # elif not path.endswith(os.sep) and not is_dir:
    #     pass
    if path.endswith(os.sep) and not is_dir:
        normalized_path = path[0:-1* len(os.sep)]  # remove seperator
    elif not path.endswith(os.sep) and is_dir:
        normalized_path = os.path.join(path, '')  # add seperator

    return normalized_path



print(normalize_path('/home/himanshu/dir/', True))
print(normalize_path('/home/himanshu/dir/', False))
print(normalize_path('/home/himanshu/file', True))
print(normalize_path('/home/himanshu/file', False))