# coding: utf-8
import random
import hashlib
import time
import hmac
import urllib.parse
import json
import os
import collections
import datetime
import itertools
import functools
import inspect

import pytz
import requests
import requests.exceptions

from . import constants
from . import helpers
from . import options

from .exceptions import *


def repeat_when_429(*args):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except args:
                time.sleep(1)
                return wrapper(*args, **kwargs)
        return wrapper
    return decorator


class InstagramClient:
    def __init__(self, username, password, proxies=None):
        self.username = username
        self.password = password
        self.uuid = self.generate_uuid()
        self.device_id = self.generate_device_id(hashlib.md5((self.username + self.password).encode(options.DEFAULT_ENCODING)).hexdigest())
        self.headers = self.get_headers()
        self.session = requests.Session()
        self.session.proxies = proxies or {}
        self.user_id = None
        self.rank_token = None
        self.csrftoken = None

    @staticmethod
    def generate_uuid(split=False):
        uuid = '%04x%04x-%04x-%04x-%04x-%04x%04x%04x' % (
            random.randint(0, 65535),
            random.randint(0, 65535),
            random.randint(0, 65535),
            random.randint(16384, 20479),
            random.randint(32768, 49151),
            random.randint(0, 65535),
            random.randint(0, 65535),
            random.randint(0, 65535)
        )
        return uuid if not split else uuid.replace('-', '')

    @staticmethod
    def generate_device_id(seed):
        volatile_seed = str(int(time.time()))
        return 'android-' + hashlib.md5((seed + volatile_seed).encode(options.DEFAULT_ENCODING)).hexdigest()[:16]

    @staticmethod
    def get_headers():
        return {
            'Connection': 'close',
            'Accept': '*/*',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie2': '$Version=1',
            'Accept-Language': 'en-US',
            'User-Agent': constants.USER_AGENT,
        }

    @staticmethod
    def get_json(response):
        if not 200 <= response.status_code <= 299:
            raise InstagramNot2XX(response.content, response.status_code)
        try:
            json_response = response.json()
        except ValueError:
            raise InstagramNotJson(response.content)
        else:
            if json_response['status'] == 'fail':
                raise InstagramFailer(json_response['message'])
            if json_response.get('errors'):
                raise InstagramFailer(str(json_response.get('errors')))
            return json_response

    def login(self):
        fetch_url = constants.API_URL + 'si/fetch_headers/?challenge_type=signup&guid=' + self.generate_uuid(split=True)
        self.session.get(fetch_url, verify=options.SSL_VERIFY)
        data = json.dumps({
            'device_id': self.device_id,
            'guid': self.uuid,
            'phone_id': self.generate_uuid(split=False),
            'username': self.username,
            'password': self.password,
            'login_attempt_count': 0
        })
        login_url = constants.API_URL + 'accounts/login/'
        response = self.session.post(login_url,
                                     data=self.generate_signature(data.encode(options.DEFAULT_ENCODING)),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)

        logged_in_user = json_response['logged_in_user']

        self.user_id = logged_in_user['pk']
        self.rank_token = str(self.user_id) + '_' + self.uuid
        self.csrftoken = response.cookies['csrftoken']

        self.sync_features()
        self.auto_complete_user_list()
        self.timeline_feed()
        self.get_recent_activity()

    def logout(self):
        response = self.session.get(constants.API_URL + 'accounts/logout/',
                                    headers=self.headers, verify=options.SSL_VERIFY)
        self.get_json(response)

    @staticmethod
    def generate_signature(data):
        hmac_key = constants.IG_SIG_KEY.encode(options.DEFAULT_ENCODING)
        if isinstance(data, str):
            data = data.encode(options.DEFAULT_ENCODING)
        digest = hmac.new(hmac_key, msg=data, digestmod=hashlib.sha256).hexdigest()
        return 'ig_sig_key_version=' + constants.SIG_KEY_VERSION + '&signed_body=' + digest + '.' + urllib.parse.quote_plus(data)

    def sync_features(self):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'id': self.user_id,
            '_csrftoken': self.csrftoken,
            'experiments': constants.EXPERIMENTS
        })
        return self.session.post(constants.API_URL + 'qe/sync/',
                                 data=self.generate_signature(data.encode(options.DEFAULT_ENCODING)),
                                 headers=self.headers,
                                 verify=options.SSL_VERIFY)

    def auto_complete_user_list(self):
        return self.session.get(constants.API_URL + 'friendships/autocomplete_user_list/',
                                headers=self.headers, verify=options.SSL_VERIFY)

    def timeline_feed(self):
        return self.session.get(constants.API_URL + 'feed/timeline/',
                                headers=self.headers, verify=options.SSL_VERIFY)

    def get_recent_activity(self):
        response = self.session.get(constants.API_URL + 'news/inbox/?',
                                    headers=self.headers, verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def get_user_info(self, user_id):
        response = self.session.get(constants.API_URL + 'users/%d/info/' % user_id)
        json_response = self.get_json(response)
        return json_response

    def friendships(self, action, user_id):
        assert action in ['create', 'destroy', 'block', 'unblock']
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'user_id': user_id
        })
        return self.session.post(constants.API_URL + 'friendships/%s/%d/' % (action, user_id),
                                 data=self.generate_signature(data),
                                 headers=self.headers,
                                 verify=options.SSL_VERIFY)

    def follow(self, user_id, return_json=True):
        action = 'create'
        response = self.friendships(action, user_id)
        if not return_json:
            return response
        json_response = self.get_json(response)
        return json_response

    def unfollow(self, user_id, return_json=True):
        action = 'destroy'
        response = self.friendships(action, user_id)
        if not return_json:
            return response
        json_response = self.get_json(response)
        return json_response

