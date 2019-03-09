# coding: utf-8
import os
import random
import hashlib
import time
import hmac
import urllib.parse
import json
import functools
import collections
import datetime

import requests
import requests.exceptions

from . import constants
from . import utils
from . import options
from . import urls
from . import friendship_actions as actions

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
        self.session.get(urls.FETCH_URL, verify=options.SSL_VERIFY,
                         params=dict(challenge_type='signup', guid=self.generate_uuid(split=True)))
        data = json.dumps({
            'device_id': self.device_id,
            'guid': self.uuid,
            'phone_id': self.generate_uuid(split=False),
            'username': self.username,
            'password': self.password,
            'login_attempt_count': 0
        })
        response = self.session.post(urls.LOGIN_URL,
                                     data=self.generate_signature(data),
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
        response = self.session.get(urls.LOGOUT_URL, headers=self.headers, verify=options.SSL_VERIFY)
        self.get_json(response)

    @staticmethod
    def generate_signature(data):
        hmac_key = constants.IG_SIG_KEY.encode(options.DEFAULT_ENCODING)
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
        return self.session.post(urls.SYNC_URL,
                                 data=self.generate_signature(data),
                                 headers=self.headers,
                                 verify=options.SSL_VERIFY)

    def auto_complete_user_list(self):
        return self.session.get(urls.USER_LIST_URL, headers=self.headers, verify=options.SSL_VERIFY)

    def timeline_feed(self):
        return self.session.get(urls.TIMELINE_URL, headers=self.headers, verify=options.SSL_VERIFY)

    def get_recent_activity(self):
        response = self.session.get(urls.INBOX_URL, headers=self.headers, verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def expose(self):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'id': self.user_id,
            '_csrftoken': self.csrftoken,
            'experiment': 'ig_android_profile_contextual_feed',
        })
        return self.session.post(urls.EXPOSE_URL,
                                 data=self.generate_signature(data),
                                 headers=self.headers,
                                 verify=options.SSL_VERIFY)

    @staticmethod
    def build_body(bodies, boundary):
        boundary = boundary.encode(options.DEFAULT_ENCODING)
        body = b''
        for b in bodies:
            body += b'--' + boundary + b'\r\n'
            body += f'Content-Disposition: {b["type"]}; name="{b["name"]}"'.encode(options.DEFAULT_ENCODING)
            filename = b.get('filename')
            if filename:
                _, ext = os.path.splitext(filename)
                body += f'; filename="pending_media_{str(int(time.time() * 1000))}{ext}"'.encode(options.DEFAULT_ENCODING)
            headers = b.get('headers')
            if headers and isinstance(headers, collections.Iterable):
                for header in headers:
                    body += b'\r\n' + header.encode(options.DEFAULT_ENCODING)
            encoded_data = b['data'] if isinstance(b['data'], bytes) else b['data'].encode(options.DEFAULT_ENCODING)
            body += b'\r\n\r\n' + encoded_data + b'\r\n'
        body += b'--' + boundary + b'--'
        return body

    def upload_photo(self, photo_path, uid=None, caption=''):
        upload_url = urls.UPLOAD_IMG_URL
        boundary = self.uuid
        with open(photo_path, 'rb') as photo_file:
            photo_binary = photo_file.read()
        if uid is None:
            uid = str(int(time.time() * 1000))
        bodies = [
            {'type': 'form-data',
             'name': 'upload_id',
             'data': uid},
            {'type': 'form-data',
             'name': '_uuid',
             'data': self.uuid},
            {'type': 'form-data',
             'name': '_csrftoken',
             'data': self.csrftoken},
            {'type': 'form-data',
             'name': 'image_compression',
             'data': '{"lib_name":"jt","lib_version":"1.3.0","quality":"70"}'},
            {'type': 'form-data',
             'name': 'photo',
             'data': photo_binary,
             'filename': 'pending_media_%s.jpg' % uid,
             'headers': [
                 'Content-Transfer-Encoding: binary',
                 'Content-type: application/octet-stream',
             ]},
        ]

        headers = {
            'Connection': 'close',
            'Accept': '*/*',
            'Content-type': 'multipart/form-data; boundary=' + boundary,
            'Accept-Language': 'en-US',
            'Accept-Encoding': 'gzip',
            'Cookie2': '$Version=1',
            'User-Agent': constants.USER_AGENT,
        }
        response = self.session.post(upload_url, data=self.build_body(bodies, boundary), headers=headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        upload_id = json_response['upload_id']
        self.configure(upload_id, photo_path, caption=caption)
        self.expose()

    def configure(self, upload_id, photo_path, caption=''):
        width, height = utils.picture.get_image_size(photo_path)
        data = json.dumps({
            'upload_id': upload_id,
            'camera_model': 'HM1S',
            'source_type': 4,
            'date_time_original': datetime.datetime.now().strftime('%Y:%m:%d %H:%M:%S'),
            'camera_make': 'XIAOMI',
            'edits': {
                'crop_original_size': [width, height],
                'crop_zoom': 1.0,
                'crop_center': [0.0, -0.0],
            },
            'extra': {
                'source_width': width,
                'source_height': height,
            },
            'device': {
                'manufacturer': 'Xiaomi',
                'model': 'HM 1SW',
                'android_version': 18,
                'android_release': '4.3',
            },
            '_csrftoken': self.csrftoken,
            '_uuid': str(self.uuid),
            '_uid': self.user_id,
            'caption': caption,
        })
        response = self.session.post(urls.CONF_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def upload_video(self, video_path, caption='', debug=False):
        video_path = utils.video.prepare_video(video_path, debug=debug)
        boundary = self.uuid
        with open(video_path, 'rb') as photo_file:
            video_binary = photo_file.read()
        uid = str(int(time.time() * 1000))
        bodies = [
            {'type': 'form-data',
             'name': 'upload_id',
             'data': uid},
            {'type': 'form-data',
             'name': '_uuid',
             'data': self.uuid},
            {'type': 'form-data',
             'name': '_csrftoken',
             'data': self.csrftoken},
            {'type': 'form-data',
             'name': 'media_type',
             'data': '2'},
        ]
        headers = {
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'Content-type': 'multipart/form-data; boundary=' + boundary,
            'Accept-Language': 'en-US',
            'User-Agent': constants.USER_AGENT,
        }
        response = self.session.post(urls.UPLOAD_VIDEO_URL, data=self.build_body(bodies, boundary),
                                     headers=headers, verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        video_upload_urls = json_response['video_upload_urls']
        upload_url = json_response['video_upload_urls'][3]['url']
        job = video_upload_urls[3]['job']
        chunk_count = 4
        parts = list(utils.video.split_by_parts(video_binary, chunk_count))
        for i in range(chunk_count):
            start_index, end_index, binary = parts[i]
            headers = {
                'Connection': 'keep-alive',
                'Accept': '*/*',
                'Cookie2': '$Version=1',
                'Content-type': 'application/octet-stream',
                'Session-ID': uid,
                'Accept-Language': 'en-US',
                'Content-Disposition': 'attachment; filename = "video.mov"',
                'Content-Length': str(end_index - start_index),
                'Content-Range': 'bytes %d-%d/%d' % (start_index, end_index - 1, len(video_binary)),
                'User-Agent': constants.USER_AGENT,
                'job': job
            }
            response = self.session.post(upload_url, data=binary,
                                         headers=headers, verify=options.SSL_VERIFY)
            if response.status_code not in (200, 201, 202):
                raise InstagramNot2XX(response.content, response.status_code)
        time.sleep(10)
        self.configure_video(uid, video_path, caption=caption)
        self.expose()

    def configure_video(self, uid, video_path, caption=''):
        url = urls.CONF_URL
        preview = utils.video.video_preview(video_path)
        self.upload_photo(preview, uid=uid, caption=caption)
        os.unlink(preview)
        duration, (width, heght) = utils.video.get_video_info(video_path)
        data = json.dumps(collections.OrderedDict((
            ('upload_id', int(uid)),
            ('source_type', '3'),
            ('poster_frame_index', 0),
            ('length', 0),
            ('audio_muted', 'false'),
            ('filter_type', '0'),
            ('video_result', 'deprecated'),
            ('clips', collections.OrderedDict((
                ('length', duration),
                ('source_type', '3'),
                ('camera_position', 'back'),
            ))),
            ('extra', collections.OrderedDict((
                ('source_width', width),
                ('source_height', heght),
            ))),
            ('device', collections.OrderedDict((
                ('manufacturer', 'Xiaomi'),
                ('model', 'HM 1SW'),
                ('android_version', 18),
                ('android_release', '4.3'),
            ))),
            ('_csrftoken', self.csrftoken),
            ('_uuid', str(self.uuid)),
            ('_uid', int(self.user_id)),
            ('caption', caption),
        )))
        headers = {
            'Connection': 'close',
            'Accept': '*/*',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept-Language': 'en-US',
            'Cookie2': '$Version=1',
            'User-Agent': constants.USER_AGENT,
        }
        data = data.replace('"length": 0', '"length": 0.00')
        response = self.session.post(url, params=dict(video='1'), data=self.generate_signature(data), headers=headers)
        return self.get_json(response)

    def get_user_info(self, user_id):
        response = self.session.get(urls.USER_INFO_URL % user_id)
        json_response = self.get_json(response)
        return json_response

    def friendships(self, action, user_id):
        assert action in actions.ACTIONS
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'user_id': user_id
        })
        return self.session.post(urls.FRIENDSHIPS_URL % (action, user_id),
                                 data=self.generate_signature(data),
                                 headers=self.headers,
                                 verify=options.SSL_VERIFY)

    def follow(self, user_id):
        action = actions.CREATE
        response = self.friendships(action, user_id)
        json_response = self.get_json(response)
        return json_response

    def unfollow(self, user_id):
        action = actions.DESTROY
        response = self.friendships(action, user_id)
        json_response = self.get_json(response)
        return json_response
