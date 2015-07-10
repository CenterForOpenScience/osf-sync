__author__ = 'himanshu'
import requests
import urllib.parse
# -H 'X-CSRFToken: qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK'
# -H 'Cookie: _pk_id.1.2840=5d8268ce2f65679d.1435256429.3.1435269530.1435269100.; osf_staging2=558c5c0e404f7759c466d76c.mvTRGjJunz78jpb5t6gsJaf4chM; _pk_ses.1.2840=*; csrftoken=qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK'
# -H 'Connection: keep-alive'
# -H 'Pragma: no-cache'
# -H 'Cache-Control: no-cache'

url = 'https://staging2.osf.io/api/v2/nodes/'

headers = {
            'Host': 'staging2.osf.io',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://staging2.osf.io/api/v2/docs/',
            'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
            #this last one is key!
            'Cookie':'_pk_id.1.2840=5d8268ce2f65679d.1435256429.11.1435537902.1435537648.; csrftoken=qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK; osf_staging2=55909114404f7771e130bd54.Uhpq9MP5TtSvEIZH8CeyLJmdnAc; _pk_id.1.0e8b=3e752283c198c4ce.1435342348.1.1435342354.1435342348.; _pk_ref.1.0e8b=%5B%22%22%2C%22%22%2C1435342348%2C%22https%3A%2F%2Fstaging2.osf.io%2F2r67q%2F%22%5D; _pk_ses.1.2840=*',
            'Origin' : 'https://staging2.osf.io',
        }

# data={
#     'title':'new himansuh project',
#     'description':'some%20description2',
#     'category':'project'
# }
#
# resp = requests.post(url, headers=headers, data=data)
# print(resp.json())



user = requests.get('https://staging2.osf.io/api/v2/', headers=headers).json()['meta']['current_user']['data']
node = requests.get(user['links']['nodes']['relation'], headers=headers).json()['data'][0]

osfstorage = requests.get(node['links']['files']['related'], headers=headers).json()['data'][0]
# import pdb;pdb.set_trace()
local_file = {'file':open('__init__.py')}


headers['Authorization'] = 'Bearer eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLkluTmc3bm00MS1pVGJtb3lZTFRGdlEuSUkwRmNQdWlWNEJyT3lXWEMzN2NRdzlQcXJCaUdHMjFZQU5WWXpNR21oSWtMMm0zMVlQUXV6U1F1WXdPOS1UTmViT01LbC1taDdpWjVZcGZBd3ZIN092ZWNEcjhRaXZScGRZaHpBbDR5QlZJYTZxZ0JKLVVhMXNUYWJ4YkoyRnVkOU1KYTIxNXJ3cHlwVVJYbjJheXRyaDRndmFMN1R1bXdsVmtEMG9ucmJCazc3djdJX3NjbFFzM1VxRXJUd0tBLlBGVGtveEdNTkNRUnZDWjVaMTI0cFE.VTDpLASAddpoknjQdd1x1EN3O8A3VJzPktfsj3_zNlDbHyGJHFhP8J-f5TR5CNqziBVr7dVnpCyie3T_oSwACA'
# #this works for sending up a folder
# remote_folder = requests.post('https://staging2-files.osf.io/file?path=%2Fisthisfoldekr%2F&provider=osfstorage&nid=dw4nt', headers=headers )
# print(remote_folder.json())

#this works for sending a file.
# desired_url='https://staging2-files.osf.io/file?path=%2Farray.h&provider=osfstorage&nid=8c6mu'
# file_url = osfstorage['links']['self'][0:osfstorage['links']['self'].index('&cookie=')]
# print('WANT:{}'.format(desired_url))
# print('ACTUAL:{}'.format(file_url))
params = {
    'path':'/filename',# os.uncommon dir name (provider path, local_file_folder.path)
    'provider':'osfstorage',
    'nid':'8c6mu'# node.osf_id
}
params_string = '&'.join([k+'='+v for k,v in params.items()])
file_url = osfstorage['links']['self'].split('?')[0] + '?' + params_string
print()

#note: don't have to delete files. Can just post to them again, and it replaces older version of file.
remote_file = requests.put(file_url,
                            headers=headers,
                            # data = local_file['file']
                            files=local_file
                            )
print(remote_file)

#
# with open(local_file_folder.path, 'wb') as fd:
#                     for chunk in resp.iter_content(2048): #todo: which is better? 1024 or 2048? Apparently, not much difference.
#                         fd.write(chunk)
#

# 'https://staging2-files.osf.io/file?path=%2Farray.h&provider=osfstorage&nid=dw4nt'
# -X PUT
# -H 'Host: staging2-files.osf.io'
# -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0'
# -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5'
# --compressed -H 'Cache-Control: no-cache'
# -H 'X-Requested-With: XMLHttpRequest'
# -H 'Authorization: Bearer eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLkluTmc3bm00MS1pVGJtb3lZTFRGdlEuSUkwRmNQdWlWNEJyT3lXWEMzN2NRdzlQcXJCaUdHMjFZQU5WWXpNR21oSWtMMm0zMVlQUXV6U1F1WXdPOS1UTmViT01LbC1taDdpWjVZcGZBd3ZIN092ZWNEcjhRaXZScGRZaHpBbDR5QlZJYTZxZ0JKLVVhMXNUYWJ4YkoyRnVkOU1KYTIxNXJ3cHlwVVJYbjJheXRyaDRndmFMN1R1bXdsVmtEMG9ucmJCazc3djdJX3NjbFFzM1VxRXJUd0tBLlBGVGtveEdNTkNRUnZDWjVaMTI0cFE.VTDpLASAddpoknjQdd1x1EN3O8A3VJzPktfsj3_zNlDbHyGJHFhP8J-f5TR5CNqziBVr7dVnpCyie3T_oSwACA'
# -H 'Referer: https://staging2.osf.io/dw4nt/'
# -H 'Content-Type: text/x-chdr'
# -H 'Origin: https://staging2.osf.io'
# -H 'Connection: keep-alive'
#
# --data $'/*\n * This file defines the API for the array type.\n *\n * Copyright (c) 2015 Riverbank Computing Limited <info@riverbankcomputing.com>\n *\n * This file is part of SIP.\n *\n * This copy of SIP is licensed for use under the terms of the SIP License\n * Agreement.  See the file LICENSE for more details.\n *\n * This copy of SIP may also used under the terms of the GNU General Public\n * License v2 or v3 as published by the Free Software Foundation which can be\n * found in the files LICENSE-GPL2 and LICENSE-GPL3 included in this package.\n *\n * SIP is supplied WITHOUT ANY WARRANTY; without even the implied warranty of\n * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n */\n\n\n#ifndef _ARRAY_H\n#define _ARRAY_H\n\n\n#include <Python.h>\n\n#include "sip.h"\n\n\n#ifdef __cplusplus\nextern "C" {\n#endif\n\n\nextern PyTypeObject sipArray_Type;\n\nPyObject *sip_api_convert_to_array(void *data, const char *format,\n        SIP_SSIZE_T len, int flags);\nPyObject *sip_api_convert_to_typed_array(void *data, const sipTypeDef *td,\n        const char *format, size_t stride, SIP_SSIZE_T len, int flags);\n\n\n#ifdef __cplusplus\n}\n#endif\n\n#endif\n'
#
