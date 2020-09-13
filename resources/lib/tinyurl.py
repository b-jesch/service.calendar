from urllib.request import urlopen
from urllib.parse import urlencode

TINYAPI = "http://tinyurl.com/api-create.php"

def create_one(url):
    url_data = urlencode(dict(url=url)).encode()
    ret = urlopen(TINYAPI, data=url_data).read().strip()
    return ret
