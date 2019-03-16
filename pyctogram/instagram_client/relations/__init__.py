from . base import Actions, get_users


def get_followers(username, password, victim_username, proxies=None):
    return get_users(username, password, victim_username, proxies=proxies, relation=Actions.followers)


def get_followings(username, password, victim_username, proxies=None):
    return get_users(username, password, victim_username, proxies=proxies, relation=Actions.followings)
