import re
import json

import requests

from .exceptions import *


def get_instagram_id(username):
    url = f'https://www.instagram.com/web/search/topsearch/?query={username}'
    data = requests.get(url, timeout=60)
    users = map(lambda r: r['user'], json.loads(data.content)['users'])
    users = list(filter(lambda u: u['username'] == username, users))
    if len(users) == 0:
        raise RuntimeError(f"Can't find user with username = {username}")
    elif len(users) > 1:
        raise RuntimeError(f"Found multiple users with username = {username}")
    else:
        user = users[0]
    return int(user['pk'])


def get_user_info(username):
    info_url = 'https://www.instagram.com/%s/'
    session = requests.Session()
    response = session.get(info_url % username)
    if response.status_code != 200:
        raise InstagramNot2XX(response.content, response.status_code)
    if response.content is None:
        raise InstagramEmptyBody
    return parse_user_info(response.text)


def parse_user_info(html_data):
    pattern = re.compile(r'<script type="text\/javascript">window\._sharedData = (.*);<\/script>')
    found = pattern.findall(html_data)
    if found:
        found = found[0]
    else:
        raise InstagramWrongJsonStruct
    json_data = json.loads(found)
    profile = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
    user_info = {
        "pk": profile["id"],
        "username": profile["username"],
        "full_name": profile["full_name"],
        "profile_pic_url": profile["profile_pic_url"],
        "profile_pic_url_hd": profile["profile_pic_url_hd"],
        "is_private": profile["is_private"],
        "is_verified": profile["is_verified"],
        "media_count": profile["edge_owner_to_timeline_media"]["count"],
        "follower_count": profile["edge_followed_by"]["count"],
        "following_count": profile["edge_follow"]["count"],
        "biography": profile["biography"],
        "external_url": profile["external_url"],
        "last_media": None,
    }
    if user_info["media_count"] > 0 and not user_info["is_private"]:
        last_media_data = profile["edge_owner_to_timeline_media"]["edges"][0]['node']
        last_media = {
            'id': f'{last_media_data["id"]}_{user_info["pk"]}',
            'url': last_media_data["display_url"],
            'taken_at': last_media_data['taken_at_timestamp'],
        }
        user_info["last_media"] = last_media
    return user_info
