import re
import json

import requests


def get_instagram_id(username):
    url = f'https://www.instagram.com/web/search/topsearch/?query={username}'
    data = requests.get(url, timeout=60)
    pk = json.loads(data.content)['users'][0]['user']['pk']
    return pk
