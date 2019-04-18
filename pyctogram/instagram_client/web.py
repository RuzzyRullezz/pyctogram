import re
import json

import requests

from .exceptions import *

TIMEOUT = 60


def get_instagram_id(username):
    url = f'https://www.instagram.com/web/search/topsearch/?query={username}'
    data = requests.get(url, timeout=TIMEOUT)
    users = map(lambda r: r['user'], json.loads(data.content)['users'])
    users = list(filter(lambda u: u['username'] == username, users))
    if len(users) == 0:
        raise RuntimeError(f"Can't find user with username = {username}")
    elif len(users) > 1:
        raise RuntimeError(f"Found multiple users with username = {username}")
    else:
        user = users[0]
    return int(user['pk'])


def get_user_info(username, session=None, proxy=None):
    info_url = 'https://www.instagram.com/%s/'
    if session is None:
        session = requests.Session()
    response = session.get(info_url % username, timeout=TIMEOUT, proxies=proxy)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise InstagramNot2XX(response.text, response.status_code)
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
    if len(profile["edge_owner_to_timeline_media"]["edges"]) > 0:
        last_media_data = profile["edge_owner_to_timeline_media"]["edges"][0]['node']
        last_media = {
            'id': f'{last_media_data["id"]}_{user_info["pk"]}',
            'url': last_media_data["display_url"],
            'taken_at': last_media_data['taken_at_timestamp'],
        }
        user_info["last_media"] = last_media
    return user_info


def get_logged_session(username, password):
    headers = {
        'cookie': 'ig_cb=1; rur=FRC; mid=XI02wQAEAAEnEs0nRXWyCFK8gT69; csrftoken=KEaXQWmABfhbyv0MJr3JYszWHRikBhI6',
        'origin': 'https://www.instagram.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/72.0.3626.121 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'x-csrftoken': 'KEaXQWmABfhbyv0MJr3JYszWHRikBhI6',
        'x-ig-app-id': '936619743392459',
        'x-instagram-ajax': '46f49c18c4f1',
        'content-type': 'application/x-www-form-urlencoded',
        'accept': '*/*',
        'referer': 'https://www.instagram.com/accounts/login/',
        'authority': 'www.instagram.com',
    }

    data = {
        'username': username,
        'password': password,
        'queryParams': '{}',
        'optIntoOneTap': 'false'
    }
    session = requests.Session()
    session.headers.update(headers)
    response = session.post('https://www.instagram.com/accounts/login/ajax/', data=data)
    if response.status_code != 200:
        raise InstagramNot2XX(response.text, response.status_code)
    return session


def session_logout(session):
    token = session.headers['x-csrftoken']
    data = {
        'csrfmiddlewaretoken': token
    }
    response = session.post('https://www.instagram.com/accounts/logout/',data=data)
    if response.status_code != 200:
        raise InstagramNot2XX(response.text, response.status_code)


def username_is_ok(username):
    headers = {
        'cookie': 'ig_cb=1; rur=FTW; mid=XLjUvgAEAAHuzKrXW84YSw5E5n5B; csrftoken=KpvfzubGlN8OUS2XvnhDDsztQetreXcq',
        'origin': 'https://www.instagram.com',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'x-csrftoken': 'KpvfzubGlN8OUS2XvnhDDsztQetreXcq',
        'x-ig-app-id': '936619743392459',
        'x-instagram-ajax': '3ecfbff24fce',
        'content-type': 'application/x-www-form-urlencoded',
        'accept': '*/*',
        'referer': 'https://www.instagram.com/',
        'authority': 'www.instagram.com',
    }
    data = {
        'email': '',
        'password': '',
        'username': username,
        'first_name': '',
        'opt_into_one_tap': 'false'
    }
    errors = requests.post(
        'https://www.instagram.com/accounts/web_create_ajax/attempt/', headers=headers, data=data
    ).json()['errors']
    username_error = errors.get('username')
    if username_error:
        return False
    else:
        return True




