import queue
import threading
import time

import requests

from ..client import InstagramClient
from ..web import get_instagram_id, get_user_info
from ..exceptions import InstagramException

CONNECTION_MAX_ATTEMPTS = 100


class Actions:
    followers = 'followers'
    followings = 'followings'

    actions = {
        followers: InstagramClient.get_followers,
        followings: InstagramClient.get_followings,
    }


def get_users(username, password, victim_username, proxies=None, relation=Actions.followers):
    input_queue = queue.Queue()
    output_queue = queue.Queue()
    proxies = proxies or [None]
    workers_count = len(proxies)

    def queue_filler():
        sleep_time = 10  # Seconds
        try:
            victim_id = get_instagram_id(victim_username)
            insta_client = InstagramClient(username, password)
            insta_client.login()
            for user_pack in Actions.actions[relation](insta_client, victim_id):
                for user_data in user_pack:
                    input_queue.put(user_data)
                time.sleep(sleep_time)
        finally:
            list(map(lambda ii: input_queue.put(None), range(workers_count)))

    def worker(proxy=None):
        try:
            while True:
                user = input_queue.get()
                if user is None:
                    break
                attempts = 0
                while True:
                    attempts += 1
                    try:
                        output_queue.put(get_user_info(user['username'], proxy=proxy))
                    except (requests.exceptions.ChunkedEncodingError, InstagramException):
                        time.sleep(float(attempts) / 2)
                        if attempts >= CONNECTION_MAX_ATTEMPTS:
                            raise
                    else:
                        break
                input_queue.task_done()
        finally:
            output_queue.put(None)

    for proxy_settings in proxies:
        t = threading.Thread(target=worker, args=(proxy_settings, ))
        t.setDaemon(True)
        t.start()

    filler = threading.Thread(target=queue_filler)
    filler.setDaemon(True)
    filler.start()

    active_threads_cnt = workers_count
    while active_threads_cnt > 0:
        user_info = output_queue.get()
        if user_info is None:
            active_threads_cnt -= 1
        else:
            yield user_info
