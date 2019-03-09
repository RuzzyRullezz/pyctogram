import os
from pyctogram.instagram_client import client
from pyctogram.tests import account

if __name__ == '__main__':
    insta_client = client.InstagramClient(account.username, account.password)
    insta_client.login()
    video_path = os.path.join(os.path.dirname(__file__), 'data', 'example.mp4')
    insta_client.upload_video(video_path)
