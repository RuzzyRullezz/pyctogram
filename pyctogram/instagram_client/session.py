import datetime
import traceback

import requests
from requests import Request

from .logger import RequestLog


class LoggedSession(requests.Session):
    def __init__(self, log_func=None):
        super().__init__()
        self.log_func = log_func

    def request(self, method, url,
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=True, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None):
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)
        log = RequestLog()
        log.request_method = prep.method
        log.request_headers = str(prep.headers)
        log.request_body = prep.body
        log.url = prep.url
        log.request_timestamp = datetime.datetime.now()
        try:
            proxies = proxies or {}

            settings = self.merge_environment_settings(
                prep.url, proxies, stream, verify, cert
            )

            send_kwargs = {
                'timeout': timeout,
                'allow_redirects': allow_redirects,
            }
            send_kwargs.update(settings)
            resp = self.send(prep, **send_kwargs)
            log.request_timestamp = datetime.datetime.now()
            log.status_code = resp.status_code
            log.response_headers = str(resp.headers)
            log.response_body = resp.content
            return resp
        except:
            log.error = traceback.format_exc()
        finally:
            if self.log_func and callable(self.log_func):
                self.log_func(log)
