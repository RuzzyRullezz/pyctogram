import requests

from ..client import InstagramClient
from ..web import get_instagram_id, get_user_info
from ..exceptions import InstagramException, InstagramNot2XX, InstagramEmptyBody

CONNECTION_MAX_ATTEMPTS = 100


class Actions:
    followers = 'followers'
    followings = 'followings'

    actions = {
        followers: InstagramClient.get_followers,
        followings: InstagramClient.get_followings,
    }


def get_users(username, password, victim_username, relation=Actions.followers):
    victim_id = get_instagram_id(victim_username)
    insta_client = InstagramClient(username, password)
    insta_client.login()
    for users_pack in Actions.actions[relation](insta_client, victim_id):
        for user in users_pack:
            attempts = 0
            while True:
                attempts += 1
                try:
                    yield get_user_info(user['username'])
                except (requests.exceptions.ChunkedEncodingError, InstagramException):
                    if attempts >= CONNECTION_MAX_ATTEMPTS:
                        raise
                else:
                    break
