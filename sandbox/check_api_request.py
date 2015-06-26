__author__ = 'himanshu'
import requests

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
    'Cookie': '_pk_id.1.2840=5d8268ce2f65679d.1435256429.3.1435269530.1435269100.; osf_staging2=558c5c0e404f7759c466d76c.mvTRGjJunz78jpb5t6gsJaf4chM; _pk_ses.1.2840=*; csrftoken=qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK'
}

data={
    'title':'new himansuh project',
    'description':'some%20description2',
    'category':'project'
}

resp = requests.post(url, headers=headers, data=data)
print(resp.json())