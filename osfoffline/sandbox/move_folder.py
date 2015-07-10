__author__ = 'himanshu'
import requests

def move():

    """
    'https://staging2-files.osf.io/ops/move'
    -H 'Authorization: Bearer eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ'
    -H 'Origin: https://staging2.osf.io'
    -H 'Accept-Encoding: gzip, deflate'
    -H 'Accept-Language: en-US,en;q=0.8'
    -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.130 Safari/537.36'
    -H 'Content-Type: Application/json'
    -H 'Accept: */*'
    -H 'Referer: https://staging2.osf.io/mk26q/'
    -H 'Connection: keep-alive'
    --data-binary '{
        "rename":"myfolderRENAMED1",
        "conflict":"replace",
        "source":{"path":"/559d71b5404f7702fefaea2d/","provider":"osfstorage","nid":"mk26q"},
        "destination":{"path":"/","provider":"osfstorage","nid":"mk26q"}}' --compressed
    """

    # self.headers =  {
    #                 # 'Host': 'staging2.osf.io',
    #                 # 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
    #                 'Accept': 'application/json',
    #                 'Accept-Language': 'en-US,en;q=0.5',
    #                 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    #                 # 'Referer': 'https://staging2.osf.io/api/v2/docs/',
    #                 # 'X-CSRFToken': 'qnlWxEzFMyJ5GH7tWv842vdocXPcwZfK',
    #                 #this last one is key!
    #                 'Cookie':'_ga=GA1.2.1042569900.1436205463; osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _pk_id.1.2840=841d2b69a87afbce.1436271936.8.1436340402.1436338347.; _pk_ses.1.2840=*',
    #                 #this one is key for files
    #                 'Authorization' : 'Bearer {}'.format(self.user.oauth_token)
    #             }
    headers =  {
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie':'_ga=GA1.2.1042569900.1436205463; osf_staging2=559c6834404f7702fafae988.8McbBgBvu98W-KKYfNEBz5FNSSo; csrftoken=zulBIXQzKzqfHjGepa8yeEevNLeydd3S; _pk_id.1.2840=841d2b69a87afbce.1436271936.8.1436340402.1436338347.; _pk_ses.1.2840=*',
        #this one is key for files
        'Authorization' : 'Bearer {}'.format('eyJhbGciOiJIUzUxMiJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1USTRRMEpETFVoVE1qVTJJbjAuLmVCS25RaW1FSFUtNHFORnZSLWw5UGcuZU1FZTRlVlNaVXR2dGh1a3V4cUhXVWdsbDY5bTJsTHlUaWM5VHcwZGNvMndFU2xsZzJpR25KUGZOanprbm9mcFc5NjBLQ1JyUVMtSmNjT2JINVpYYlZ5aTdpdTRENDNDZWxhN2tWTXk0dlVtWHByekxIRTlaMHdVUFhPd1RPdEl1b0NqNEQwX0VqMmtQLVpvamF6NVhHNjk1ZVNTMEZYYXBGZGpURFcxX2FYZFdvQlVEUm0zTjJBOGd2SkxTY0ZULk9rQ1Bwd1kzS2NUeDJTaEJkcXJPbFE.FMsFG-z-eiZ0yI_7pYTVBo9DlkfJfdT7Nwocej_0aRZHA-hxjULt-XwFD8w0m5w0JGH2yi6MFlCQDHJxPwvUaQ')
    }
    data_my = {'rename': 'myfolderOLD',
               'destination': {'path': '/', 'provider': 'osfstorage', 'nid': 'mk26q'},
               'source': {'path': '/559d71b5404f7702fefaea2d/', 'provider': 'osfstorage', 'nid': 'mk26q'},
               'conflict': 'replace'}
    import json
    resp = requests.post('https://staging2-files.osf.io/ops/move', headers=headers, data=json.dumps(data_my))
    print(resp.status_code)
    print(resp.content)

move()