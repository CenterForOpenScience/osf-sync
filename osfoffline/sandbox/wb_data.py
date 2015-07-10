__author__ = 'himanshu'
import requests


#
# def wb_data(self, local_file_folder, remote_file_folder):
#     """
#     This function is meant to be called during modifications, thus can assume both local_file_folder and remote_file_folder exist
#     """
#     assert local_file_folder is not None
#     assert remote_file_folder is not None
#     assert local_file_folder.osf_id == remote_file_folder['id']
#
#     if local_file_folder.parent:
#         #NOTE: only need 1 level up!!!!!! thats how path works in this case.
#         path = local_file_folder.parent.osf_path + local_file_folder.name
#     else:
#         path = '/{}'.format(local_file_folder.name)
#     params = {
#         'path':path,
#         'nid':local_file_folder.node_id,
#         'provider':local_file_folder.provider,
#     }
#     params_string = '&'.join([k+'='+v for k,v in params.items()])
#     WB_DATA_URL ='https://staging2-files.osf.io/data'
#     file_url = WB_DATA_URL + '?' + params_string
#
#     headers =  {
#             'Origin': 'https://staging2.osf.io',
#             'Accept-Encoding': 'gzip, deflate, sdch',
#             'Accept-Language': 'en-US,en;q=0.8',
#             'Authorization' : 'Bearer {}'.format(self.user.oauth_token),
#             'Accept': 'application/json, text/*',
#             'Referer': 'https://staging2.osf.io/{}/'.format(local_file_folder.node_id),
#             'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
#
#             # 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#             # 'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
#             #this last one is key!
#             # 'Cookie':'_ga=GA1.2.1042569900.1436205463; osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _pk_id.1.2840=841d2b69a87afbce.1436271936.8.1436340402.1436338347.; _pk_ses.1.2840=*',
#             #this one is key for files
#
#             'Connection':'keep-alive'
#         }
#
#     resp = requests.get(file_url, headers=headers)
#     if resp.ok:
#         return resp.json()


# 'https://staging2-files.osf.io/data?path=%2F559cd48a404f7702f8fae98d%2F&provider=osfstorage&nid=f7j26&_=1436363362150'
# -H 'Origin: https://staging2.osf.io'
# -H 'Accept-Encoding: gzip, deflate, sdch'
# -H 'Accept-Language: en-US,en;q=0.8'
# -H 'Authorization: Bearer eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ'
# -H 'Accept: application/json, text/*'
# -H 'Referer: https://staging2.osf.io/f7j26/'
# -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.130 Safari/537.36'
# -H 'Connection: keep-alive' \
#    --compressed


def determine_request():
    url = 'https://staging2-files.osf.io/data?path=/559d4004404f7702fefae9d0&provider=osfstorage&nid=mk26q'
    oauth_token ='eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ'
    node_id = 'mk26q'

    headers =  {
            'Origin': 'https://staging2.osf.io',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'en-US,en;q=0.8',
            'Authorization' : 'Bearer {}'.format(oauth_token),
            'Accept': 'application/json, text/*',
            'Referer': 'https://staging2.osf.io/{}/'.format(node_id),
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',

            # 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
            #this last one is key!
            # 'Cookie':'_ga=GA1.2.1042569900.1436205463; osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _pk_id.1.2840=841d2b69a87afbce.1436271936.8.1436340402.1436338347.; _pk_ses.1.2840=*',
            #this one is key for files

            'Connection':'keep-alive'
        }
    print(url)
    resp = requests.get(url, headers=headers)
    print("{}:{}".format(resp.status_code,resp.content))

determine_request()