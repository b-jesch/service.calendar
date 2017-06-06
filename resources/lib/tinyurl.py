import urllib

TINYAPI = "http://tinyurl.com/api-create.php"

def create_one(url):
    url_data = urllib.urlencode(dict(url=url))
    ret = urllib.urlopen(TINYAPI, data=url_data).read().strip()
    return ret
