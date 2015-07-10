__author__ = 'himanshu'

from datetime import datetime
import iso8601
import requests

node = requests.get('https://staging2.osf.io/api/v2/nodes').json()['data'][0]
timestamp = node['date_modified']
print("given:",timestamp)
utc_datetime = iso8601.parse_date("20150612T16:12:50.752000")
print("datetime:",utc_datetime)

