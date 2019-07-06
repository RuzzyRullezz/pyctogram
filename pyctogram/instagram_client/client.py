# coding: utf-8
import os
import random
import hashlib
import re
import time
import hmac
import urllib.parse
import json
import urllib
import collections
import datetime
import pickle

import requests
import requests.exceptions

from . import constants
from . import utils
from . import options
from . import urls
from . import friendship_actions as actions
from . import session
from . import web
from . exceptions import *


class InstagramClient:
    def __init__(self, username, password, proxies=None, login_cookies=None, log_func=None, session_file=None):
        self.username = username
        self.password = password
        self.restored = False
        self.session_file = session_file
        if session_file and os.path.isfile(session_file):
            restored_client = self.restore_client(session_file)
            if restored_client.username != self.username or restored_client.password != self.password:
                raise RuntimeError("Client credentials doesn't match")
            self.__dict__.update(restored_client.__dict__)
            self.restored = True
            self.session.timeout = session.LoggedSession.default_timeout
            self.session.log_func = log_func
            return
        self.logged_in = False
        self.uuid = self.generate_uuid()
        self.device_id = self.generate_device_id(hashlib.md5((self.username + self.password).encode(options.DEFAULT_ENCODING)).hexdigest())
        self.phone_id = self.generate_phone_id()
        self.headers = self.get_headers()
        self.session = session.LoggedSession(log_func=log_func)
        self.session.proxies = proxies or {}
        self.login_cookies = login_cookies
        self.user_id = None
        self.rank_token = None
        self.csrftoken = None
        self.advertising_id = self.generate_uuid()
        self.session_id = self.generate_uuid()
        self.zero_rating_token = None

    @staticmethod
    def get_fake_client():
        return InstagramClient('', '')

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

    def generate_phone_id(self):
        return self.generate_uuid(split=False)

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
        if response is None:
            raise InstagramNoneResponse("Response is None")
        if not 200 <= response.status_code <= 299:
            if response.status_code == 404:
                raise Instagram404(response.text, response.status_code)
            if 500 <= response.status_code <= 599:
                raise Instagram5XX(response.text, response.status_code)
            if response.status_code == 408:
                raise InstagramRequestTimeout(response.text, response.status_code)
            try:
                json_response = response.json()
            except ValueError:
                pass
            else:
                er_msg = json_response.get('message')
                special_exception_cls = InstagramNot2XX.get_special_exception(er_msg)
                if special_exception_cls:
                    raise special_exception_cls(response.text, response.status_code)
            raise InstagramNot2XX(response.text, response.status_code)
        try:
            json_response = response.json()
        except ValueError:
            raise InstagramNotJson(response.text)
        else:
            if json_response['status'] == 'fail':
                raise InstagramFailer(json_response['message'])
            if json_response.get('errors'):
                raise InstagramFailer(str(json_response.get('errors')))
            return json_response

    def get_auth_params(self):
        return {
            'id': self.user_id,
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
        }

    def read_msisdn_header(self):
        extra_headers = {
            'X-DEVICE-ID': self.uuid,
        }
        data = json.dumps({
            'device_id': self.uuid,
            'mobile_subno_usage': 'ig_select_app',

        })
        extra_headers.update(self.headers)
        response = self.session.post(urls.READ_MSISDN_HEADER_URL,
                                     data=self.generate_signature_v2(data),
                                     headers=extra_headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def sync_device_features_v2(self):
        extra_headers = {
            'X-DEVICE-ID': self.uuid,
        }
        data = json.dumps({
            'id': self.uuid,
            'experiments': constants.EXPERIMENTS
        })
        extra_headers.update(self.headers)
        response = self.session.post(urls.SYNC_URL_V2,
                                 data=self.generate_signature_v2(data),
                                 headers=extra_headers,
                                 verify=options.SSL_VERIFY)
        self.csrftoken = response.cookies['csrftoken']
        return self.get_json(response)

    def sync_launcher(self):
        data = {
            '_csrftoken': self.csrftoken,
            'configs': constants.CONFIG,
            'id': self.uuid,
        }
        if self.logged_in:
            data.update(self.get_auth_params())
        data = json.dumps(data)
        response = self.session.post(urls.LAUNCHER_SYNC,
                                     data=self.generate_signature_v2(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def log_attribution(self):
        data = json.dumps({
            'adid': self.advertising_id,
        })
        response = self.session.post(urls.LOG_ATTRIBUTION_URL,
                                     data=self.generate_signature_v2(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def fetch_zero_rating_token(self):
        data = json.dumps({
            'custom_device_id': self.uuid,
            'device_id': self.device_id,
            'fetch_reason': 'token_expired',
            'token_hash': '',
        })
        response = self.session.post(urls.FETCH_ZERO_RATING_TOKEN,
                                     data=self.generate_signature_v2(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        self.zero_rating_token = json_response['token']['token_hash']
        return json_response

    def set_contact_point_prefill(self):
        data = json.dumps({
            'phone_id': self.phone_id,
            '_csrftoken': self.csrftoken,
            'usage': 'prefill',
        })
        response = self.session.post(urls.LOG_ATTRIBUTION_URL,
                                     data=self.generate_signature_v2(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def prelogin_v2(self):
        self.read_msisdn_header()
        self.sync_device_features_v2()
        self.sync_launcher()
        self.log_attribution()
        self.fetch_zero_rating_token()
        self.set_contact_point_prefill()

    def send_login_v2(self):
        data = json.dumps({
            'country_codes': '[{"country_code":"1","source":["default","sim"]}]',
            'phone_id': self.phone_id,
            '_csrftoken': self.csrftoken,
            'username': self.username,
            'adid': self.advertising_id,
            'guid': self.uuid,
            'device_id': self.device_id,
            'password': self.password,
            'google_tokens': '[]',
            'login_attempt_count': 0
        })
        response = self.session.post(urls.LOGIN_URL_V2,
                                     data=self.generate_signature_v2(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        logged_in_user = json_response['logged_in_user']
        self.user_id = logged_in_user['pk']
        self.rank_token = str(self.user_id) + '_' + self.uuid
        self.csrftoken = response.cookies['csrftoken']
        return json_response

    def sync_user_features(self):
        extra_headers = {
            'X-DEVICE-ID': self.uuid,
        }
        data = {
            'id': self.user_id,
            'experiments': constants.EXPERIMENTS
        }
        data.update(self.get_auth_params())
        data = json.dumps(data)
        extra_headers.update(self.headers)
        response = self.session.post(urls.SYNC_URL_V2,
                                     data=self.generate_signature_v2(data),
                                     headers=extra_headers,
                                     verify=options.SSL_VERIFY)
        self.csrftoken = response.cookies['csrftoken']
        return self.get_json(response)

    def get_feed_timeline(self):
        extra_headers = {
            'X-Ads-Opt-Out': '0',
            'X-Google-AD-ID': self.advertising_id,
            'X-DEVICE-ID': self.uuid,
        }
        extra_headers.update(self.headers)
        data = {
            '_csrftoken': self.csrftoken,
            '_uuid': self.uuid,
            'is_prefetch': '0',
            'phone_id': self.phone_id,
            'device_id': self.device_id,
            'client_session_id': self.session_id,
            'battery_level': random.randint(25, 100),
            'is_charging': '0',
            'will_sound_on': '1',
            'is_on_screen': 'true',
            'timezone_offset': '0',
            'is_async_ads_in_headload_enabled': '0',
            'is_async_ads_double_request': '0',
            'is_async_ads_rti': '0',
            'rti_delivery_backend': '0',
            'reason': 'cold_start_fetch',
            'is_pull_to_refresh': '0',
            'seen_post': '',
            'unseen_posts': '',
            'feed_view_info': '',
            'recovered_from_crash': '1',
        }
        data = urllib.parse.urlencode(data, quote_via=urllib.parse.quote_plus)
        response = self.session.post(urls.FEED_TIMELINE_URL,
                                     data=data,
                                     headers=extra_headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def get_reels_tray_feed(self):
        data = urllib.parse.urlencode({
            'supported_capabilities_new': json.dumps(constants.SUPPORT_CAPABILITIES),
            'reason': 'pull_to_refresh',
            '_csrftoken': self.csrftoken,
            '_uuid': self.uuid,
        }, quote_via=urllib.parse.quote_plus)
        response = self.session.post(urls.FEED_REELS_TRAY,
                                     data=data,
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_suggested_search(self, search_type):
        data = {'type': search_type}
        data = json.dumps(data)
        response = self.session.post(urls.SUGGESTED_SEARCH_URL,
                                     data=data,
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_recent_searches(self):
        response = self.session.post(urls.RECENT_SEARCHES_URL, headers=self.headers, verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_ranked_recipients(self, mode):
        params = {
            'mode': mode,
            'show_threads': 'true',
            'use_unified_inbox': 'true'
        }
        response = self.session.get(urls.RANKED_RECIPIENTS_URL,
                                     data=params,
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_inbox(self):
        params = {
            'persistentBadging': 'true',
            'use_unified_inbox': 'true',
        }
        response = self.session.get(urls.INBOX_URL_V2,
                                    data=params,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_presences(self):
        response = self.session.get(urls.PRESENCE_URL,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_recent_activity_inbox(self):
        response = self.session.get(urls.NEWS_INBOX_URL,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_profile_notice(self):
        response = self.session.get(urls.PROFILE_NOTICE_URL,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_blocked_media(self):
        response = self.session.get(urls.BLOCKED_MEDIA_URL,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_bootstrap_users(self):
        params = {
            'surfaces': json.dumps(constants.SURFACES)
        }
        response = self.session.get(urls.BOOTSTRAP_USERS_URL,
                                    params=params,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_explore_feed(self):
        params = {
            'is_prefetch': False,
            'is_from_promote': False,
            'timezone_offset': '0',
            'session_id': self.session_id,
            'supported_capabilities_new': json.dumps(constants.SUPPORT_CAPABILITIES)
        }
        response = self.session.get(urls.EXPLORE_URL,
                                    params=params,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_qp_fetch(self):
        data = json.dumps({
            'vc_policy': 'default',
            '_csrftoken': self.csrftoken,
            '_uid': self.user_id,
            '_uuid': self.uuid,
            'surfaces_to_queries': json.dumps({
                constants.SURFACE_PARAM[0]: constants.QP_QUERY,
                constants.SURFACE_PARAM[1]: constants.QP_QUERY,
            }),
            'version': 1,
            'scale': 2,
        })
        response = self.session.post(urls.QP_FETCH_URL,
                                    data=self.generate_signature_v2(data),
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_fb_ota(self):
        params = {
            'fields': constants.FACEBOOK_OTA_FIELDS,
            'custom_user_id': self.user_id,
            'signed_body': self.generate_signature_v2('') + '.',
            'ig_sig_key_version': constants.SIG_KEY_VERSION,
            'version_code': constants.VERSION_CODE,
            'version_name': constants.IG_VERSION,
            'custom_app_id': constants.FACEBOOK_ORCA_APPLICATION_ID,
            'custom_device_id': self.device_id
        }
        response = self.session.get(urls.FB_OTA_URL,
                                    params=params,
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)

    def postlogin_v2(self):
        self.sync_launcher()
        self.sync_user_features()
        self.get_feed_timeline()
        self.get_reels_tray_feed()
        self.get_suggested_search('users')
        self.get_recent_searches()
        self.get_suggested_search('blended')
        self.fetch_zero_rating_token()
        self.get_ranked_recipients('reshare')
        self.get_ranked_recipients('raven')
        self.get_inbox()
        self.get_presences()
        self.get_recent_activity_inbox()
        self.get_profile_notice()
        self.get_blocked_media()
        self.get_bootstrap_users()
        self.get_explore_feed()
        self.get_qp_fetch()
        self.get_fb_ota()

    def pickle_data(self):
        with open(self.session_file, 'wb') as wf:
            pickle.dump(self, wf)

    @staticmethod
    def restore_client(pickle_file):
        with open(pickle_file, "rb") as rf:
            return pickle.load(rf)

    def login_v2(self):
        self.prelogin_v2()
        self.send_login_v2()
        self.postlogin_v2()
        self.logged_in = True

    def login_v1(self):
        fetch_response = self.session.get(urls.FETCH_URL, verify=options.SSL_VERIFY, headers=self.headers,
                                          params=dict(challenge_type='signup', guid=self.generate_uuid(split=True)))
        self.get_json(fetch_response)
        data = json.dumps({
            'device_id': self.device_id,
            'guid': self.uuid,
            'phone_id': self.phone_id,
            'username': self.username,
            'password': self.password,
            'login_attempt_count': 0
        })
        response = self.session.post(urls.LOGIN_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     cookies=self.login_cookies,
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
        self.logged_in = True

    def login(self):
        if self.logged_in:
            return
        login_method = self.login_v2
        login_method()
        if self.session_file:
            self.pickle_data()

    def logout(self):
        response = self.session.get(urls.LOGOUT_URL, headers=self.headers, verify=options.SSL_VERIFY)
        self.logged_in = False
        return self.get_json(response)

    @staticmethod
    def generate_signature(data):
        hmac_key = constants.IG_SIG_KEY.encode(options.DEFAULT_ENCODING)
        data = data.encode(options.DEFAULT_ENCODING)
        digest = hmac.new(hmac_key, msg=data, digestmod=hashlib.sha256).hexdigest()
        return 'ig_sig_key_version=' + constants.SIG_KEY_VERSION + '&signed_body=' + digest + '.' + urllib.parse.quote_plus(data)

    @staticmethod
    def generate_signature_v2(data):
        hmac_key = constants.IG_SIG_KEY.encode(options.DEFAULT_ENCODING)
        data = data.encode(options.DEFAULT_ENCODING)
        digest = hmac.new(hmac_key, msg=data, digestmod=hashlib.sha256).hexdigest()
        return 'signed_body=' + digest + '.' + data.decode() + '&ig_sig_key_version=' + constants.SIG_KEY_VERSION

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
        response = self.session.post(urls.EXPOSE_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

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
        configure_response = self.configure(upload_id, photo_path, caption=caption)
        self.expose()
        return configure_response

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
                raise InstagramNot2XX(response.text, response.status_code)
        time.sleep(10)
        configure_response = self.configure_video(uid, video_path, caption=caption)
        self.expose()
        return configure_response

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

    def delete_media(self, media_id):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'media_id': media_id,
        })
        response = self.session.post(urls.DELETE_MEDIA_URL % media_id,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def direct_share(self, media_id, recipients, text=''):
        if not isinstance(recipients, collections.Iterable):
            recipients = [recipients]
        recipient_users = ','.join(map(lambda r: f'"{r}"', recipients))
        boundary = self.uuid
        bodies = [
            {'type': 'form-data',
             'name': 'media_id',
             'data': media_id},
            {'type': 'form-data',
             'name': 'recipient_users',
             'data': '[[%s]]' % recipient_users},
            {'type': 'form-data',
             'name': 'client_context',
             'data': self.uuid},
            {'type': 'form-data',
             'name': 'thread_ids',
             'data': '["0"]'},
            {'type': 'form-data',
             'name': 'text',
             'data': text.encode('utf-8')},
        ]
        data = self.build_body(bodies, boundary)
        headers = {
            'Proxy-Connection': 'keep-alive',
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'Content-type': 'multipart/form-data; boundary=' + boundary,
            'Accept-Language': 'en-US',
            'User-Agent': constants.USER_AGENT,
        }
        response = self.session.post(urls.DIRECT_SHARE_URL,
                                     params=dict(media_type='photo'),
                                     data=data,
                                     headers=headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def direct_message(self, recipients, text):
        if not isinstance(recipients, collections.Iterable):
            recipients = [recipients]
        recipient_users = ','.join(map(lambda r: '"%s"' % r, recipients))
        boundary = self.uuid
        bodies = [
            {'type': 'form-data',
             'name': 'recipient_users',
             'data': '[[%s]]' % recipient_users},
            {'type': 'form-data',
             'name': 'client_context',
             'data': self.uuid},
            {'type': 'form-data',
             'name': 'thread_ids',
             'data': '["0"]'},
            {'type': 'form-data',
             'name': 'text',
             'data': text.encode('utf-8')},
        ]
        data = self.build_body(bodies, boundary)
        headers = {
            'Proxy-Connection': 'keep-alive',
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'Content-type': 'multipart/form-data; boundary=' + boundary,
            'Accept-Language': 'en-US',
            'User-Agent': constants.USER_AGENT,
        }
        response = self.session.post(urls.DIRECT_MSG_URL,
                                     data=data,
                                     headers=headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def change_profile_picture(self, photo_path):
        with open(photo_path, 'rb') as photo_file:
            photo_binary = photo_file.read()
        boundary = self.uuid
        udata = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
        })

        bodies = [
            {'type': 'form-data',
             'name': 'ig_sig_key_version',
             'data': constants.SIG_KEY_VERSION},
            {'type': 'form-data',
             'name': 'signed_body',
             'data': self.generate_signature(udata) + udata},
            {'type': 'form-data',
             'name': 'profile_pic',
             'data': photo_binary,
             'filename': 'profile_pic.jpeg',
             'headers': [
                 'Content-Transfer-Encoding: binary',
                 'Content-type: application/octet-stream',
             ]},
            ]
        headers = {
            'Proxy-Connection': 'keep-alive',
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'Content-type': 'multipart/form-data; boundary=' + boundary,
            'Accept-Language': 'en-US',
            'Accept-Encoding': 'gzip',
            'Cookie2': '$Version=1',
            'User-Agent': constants.USER_AGENT,
        }
        data = self.build_body(bodies, boundary)
        response = self.session.post(urls.CHANGE_PROF_PHOTO_URL,
                                     data=data,
                                     headers=headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def edit_profile(self, username, email, gender, first_name=None,
                     biography=None, external_url=None, phone_number=None):
        request = {
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'device_id': self.device_id,
        }
        request.update({
            'username': username,
            'first_name': first_name,
            'email': email,
            'biography': biography,
            'external_url': external_url,
            'gender': gender,
            'phone_number': phone_number,
        })
        data = json.dumps(request)
        response = self.session.post(urls.EDIT_PROF_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
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
        friendship_status = json_response['friendship_status']
        if not friendship_status['following'] and not friendship_status['outgoing_request']:
            raise InstagramDidntChangeTheStatus("Ig didn't change the friendship status after following")
        return json_response

    def unfollow(self, user_id):
        action = actions.DESTROY
        response = self.friendships(action, user_id)
        json_response = self.get_json(response)
        friendship_status = json_response['friendship_status']
        if friendship_status['following'] or friendship_status['outgoing_request']:
            raise InstagramDidntChangeTheStatus("Ig didn't change the friendship status after unfollwong")
        return json_response

    def like(self, media_id):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'media_id': media_id
        })

        response = self.session.post(urls.LIKE_URL % media_id,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def comment(self, media_id, text):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'comment_text': text
        })

        response = self.session.post(urls.COMMENT_URL % media_id,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def get_followings(self, user_id):
        max_id = None
        url = urls.FOLLOWING_URL % user_id
        while True:
            if max_id:
                params = dict(max_id=max_id, big_list='true')
            else:
                params = {}
            list_response = self.session.post(url, params=params, headers=self.headers)
            list_response = self.get_json(list_response)
            map(lambda u: u.update({'id': u['pk']}), list_response['users'])
            yield list_response['users']
            max_id = list_response.get('next_max_id')
            if max_id is None:
                break

    def get_followers(self, user_id):
        url = urls.FOLLOWERS_URL % user_id
        max_id = None
        while True:
            if max_id:
                params = dict(max_id=max_id, big_list='true')
            else:
                params = {}
            list_response = self.session.post(url, params=params, headers=self.headers)
            list_response = self.get_json(list_response)
            yield list_response['users']
            max_id = list_response.get('next_max_id')
            if max_id is None:
                break

    def get_user_info(self, user_id):
        response = self.session.get(urls.USER_INFO_URL % user_id)
        json_response = self.get_json(response)["user"]
        user_info = {
            "pk": json_response["pk"],
            "username": json_response["username"],
            "full_name": json_response["full_name"],
            "is_private": json_response["is_private"],
            "profile_pic_url": json_response["profile_pic_url"],
            "is_verified": json_response["is_verified"],
            "media_count": json_response["media_count"],
            "follower_count": json_response["follower_count"],
            "following_count": json_response["following_count"],
            "biography": json_response["biography"],
            "external_url": json_response["external_url"],
            "profile_pic_url_hd": json_response["hd_profile_pic_versions"][-1]["url"],
            "last_media": None,
        }
        return user_info

    def get_user_friendship(self, user_id):
        response = self.session.get(urls.FRIENDSHIPS_INFO_URL % user_id, headers=self.headers)
        json_response = self.get_json(response)
        return json_response

    def get_geo_media(self, user_id, fails=0):
        falls_cnt = 10
        try:
            response = self.session.get(urls.MAPS_URL % user_id,
                                        headers=self.headers,
                                        verify=options.SSL_VERIFY)
            json_response = self.get_json(response)
        except BaseException:
            if fails >= falls_cnt:
                raise
            time.sleep(1)
            return self.get_geo_media(user_id, fails=fails+1)
        return json_response

    def get_user_feed(self, user_id):
        max_id = None
        c = 0
        url = urls.FEED_URL % user_id
        params = dict(rank_token=self.rank_token, ranked_content='true')
        while True:
            if max_id:
                params.update(dict(max_id=max_id))
            while True:
                try:
                    response = self.session.get(
                        url,
                        params=params,
                        headers=self.headers,
                        verify=options.SSL_VERIFY
                    )
                except requests.exceptions.ConnectionError:
                    continue
                else:
                    break
            json_response = self.get_json(response)
            c += len(json_response['items'])
            for item in json_response['items']:
                yield item
            max_id = json_response.get('next_max_id')
            if max_id is None:
                break

    def get_last_media_id(self, user_id):
        try:
            last_feed = next(self.get_user_feed(user_id))
        except StopIteration:
            return None
        else:
            return last_feed

    def media_info(self, media_id):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'media_id': media_id
        })
        response = self.session.post(urls.MEDIA_INFO_URL % media_id,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def get_media_comments(self, media_id):
        max_id = None
        c = 0
        url = urls.MEDIA_INFO_URL % media_id
        while True:
            if max_id:
                params = dict(max_id=max_id)
            else:
                params = {}
            response = self.session.post(url, params=params, headers=self.headers, verify=options.SSL_VERIFY)
            json_response = self.get_json(response)
            c += len(json_response['comments'])
            yield json_response['comments']
            max_id = json_response.get('next_max_id')
            if max_id is None:
                break

    def edit_media(self, media_id, user_id=None, position=None, caption=''):
        main_data = {
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'caption_text': caption,
        }
        if user_id and position:
            main_data.update({
                'usertags': json.dumps({
                    'removed': [],
                    'in': [{
                        'position': position,
                        'user_id': user_id,
                    }]
                })
            })
        data = json.dumps(main_data)
        response = self.session.post(urls.EDIT_MEDIA_URL % media_id,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response

    def tag_user(self, media_id, user_id, position, caption=''):
        return self.edit_media(media_id, user_id=user_id, position=position, caption=caption)

    def get_pending_friendships(self, max_id=None):
        url = urls.PENDING_FRIENDSHIPS_URL
        while True:
            if max_id:
                params = dict(max_id=max_id, big_list='true')
            else:
                params = {}
            list_response = self.session.post(url, params=params, headers=self.headers)
            list_response = self.get_json(list_response)
            yield list_response['users']
            max_id = list_response.get('next_max_id')
            if max_id is None:
                break

    def get_outgoing_requests(self, cursor=None):
        pattern = re.compile(r'<script type="text\/javascript">window\._sharedData = (.*);<\/script>')
        url = urls.OUTGOING_REQUESTS_URL
        while True:
            if cursor:
                html_parse = False
                params = {
                    '__a': 1,
                    'cursor': cursor,
                }
            else:
                html_parse = True
                params = {}
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                raise InstagramNot2XX(response.text, response.status_code)
            if html_parse:
                found = pattern.findall(response.text)
                if found:
                    found = found[0]
                    settings_pages_data = json.loads(found)['entry_data']['SettingsPages'][0]['data']
                else:
                    raise InstagramWrongJsonStruct
            else:
                settings_pages_data = response.json()['data']
            users_list = settings_pages_data['data']
            cursor = settings_pages_data.get('cursor')
            for user in users_list:
                yield web.get_user_info(user['text'])
            if cursor is None:
                break

    def check_username(self, username):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'username': username
        })
        response = self.session.post(urls.CHECK_USERNAME_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        return json_response['available']

    def change_password(self, new_password):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'old_password': self.password,
            'new_password1': new_password,
            'new_password2': new_password,
        })
        response = self.session.post(urls.CHANGE_PASSWORD_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        json_response = self.get_json(response)
        assert json_response['status'] == 'ok'
        self.password = new_password

    def send_confirm_email(self):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'send_source': 'edit_profile'
        })
        response = self.session.post(urls.SEND_CONFIRM_EMAIL_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        self.get_json(response)

    def send_sms_code(self, phone):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'phone_number': phone,
        })
        response = self.session.post(urls.SEND_SMS_CODE_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        self.get_json(response)

    def verify_sms_code(self, phone, code):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'phone_number': phone,
            'verification_code': code,
        })
        response = self.session.post(urls.VERIFY_SMS_CODE_URL,
                                     data=self.generate_signature(data),
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        self.get_json(response)

    def register_push(self, token):
        data = urllib.parse.urlencode({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'guid': self.uuid,
            'phone_id': self.phone_id,
            'device_token': token,
            'device_type': 'android_mqtt',
            'is_main_push_channel': True,
            'users': self.user_id,
        })
        response = self.session.post(urls.PUSH_REGISTER,
                                     data=data,
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def get_user_story_feed(self, user_id):
        supported_capabilities = json.dumps([
            {'name': 'SUPPORTED_SDK_VERSIONS',
             'value': '13.0,14.0,15.0,16.0,17.0,18.0,19.0,20.0,21.0,22.0,23.0,24.0,25.0,26.0,27.0,28.0,29.0,30.0,31.0,'
                      '32.0,33.0,34.0,35.0,36.0,37.0,38.0,39.0,40.0,41.0,42.0,43.0,44.0,45.0,46.0,47.0,48.0,49.0,50.0,'
                      '51.0,52.0,53.0,54.0,55.0,56.0,57.0,58.0'},
            {'name': 'FACE_TRACKER_VERSION',
             'value': '12'},
            {'name': 'segmentation',
             'value': 'segmentation_enabled'},
            {'name': 'COMPRESSION',
             'value': 'ETC2_COMPRESSION'},
            {'name': 'world_tracker',
             'value': 'world_tracker_enabled'},
            {'name': 'gyroscope',
             'value': 'gyroscope_enabled'},
        ])
        data = {'supported_capabilities_new': supported_capabilities}
        response = self.session.get(urls.GET_STORY_FEED_URL % user_id,
                                     data=data,
                                     headers=self.headers,
                                     verify=options.SSL_VERIFY)
        return self.get_json(response)

    def mark_media_seen(self, items):
        reels = {}
        max_seen_at = int(time.time())
        seen_at = max_seen_at - 3 * len(items)
        for item in items:
            item_taken_at = item['taken_at']
            if seen_at < item_taken_at:
                seen_at = item_taken_at + 2
            if seen_at > max_seen_at:
                seen_at = max_seen_at
            item_source_id = item['user']['pk']
            reel_id = f'{item["id"]}_{item_source_id}'
            reels[reel_id] = [f'{item_taken_at}_{seen_at}']
            seen_at += random.randint(1, 3)
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.csrftoken,
            'container_module': 'feed_timeline',
            'reels': reels,
            'reel_media_skipped': [],
            'live_vods': [],
            'live_vods_skipped': [],
            'nuxes': [],
            'nuxes_skipped': [],
        }).replace(' ', '')
        response = self.session.post(urls.MEDIA_SEEN_URL,
                                    data=self.generate_signature(data),
                                    headers=self.headers,
                                    verify=options.SSL_VERIFY)
        return self.get_json(response)
