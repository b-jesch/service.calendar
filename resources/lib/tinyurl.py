from urllib.request import urlopen
from urllib.parse import urlencode

TINYAPI = "http://tinyurl.com/api-create.php"


def create_one(url):
    url_data = urlencode(dict(url=url)).encode()
    return urlopen(TINYAPI, data=url_data).read().strip()
