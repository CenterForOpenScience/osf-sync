__author__ = 'himanshu'
import requests
from pprint import pprint
def get_logs():
    """
    curl
    'https://staging2.osf.io/api/v1/project/zrkhm/log/?page=0&_=1436579859451'
    -H 'Cookie: osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; _pk_ref.1.0e8b=%5B%22%22%2C%22%22%2C1436454261%2C%22https%3A%2F%2Fstaging2.osf.io%2F4kz8v%2F%22%5D; _pk_id.1.0e8b=f518fec328e3aab8.1436363330.6.1436454654.1436454261.; tabstyle=html-tab; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _ga=GA1.2.520806478.1436368757; _pk_id.1.2840=841d2b69a87afbce.1436271936.26.1436579860.1436578614.; _pk_ses.1.2840=*'
    -H 'Accept-Encoding: gzip, deflate, sdch'
    -H 'Accept-Language: en-US,en;q=0.8'
    -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.130 Safari/537.36'
    -H 'Accept: */*'
    -H 'Referer: https://staging2.osf.io/zrkhm/'
    -H 'X-Requested-With: XMLHttpRequest'
    -H 'Connection: keep-alive'
    -H 'Cache-Control: max-age=0' --compressed

    :return:
    """

    headers = {
        'Cookie':'osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; '
    }
    url = 'https://staging2.osf.io/api/v1/project/zrkhm/log/'
    resp = requests.get(url, headers=headers)
    pprint(resp.json())


get_logs()