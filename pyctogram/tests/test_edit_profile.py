import os
from pyctogram.instagram_client import client

if __name__ == '__main__':
    insta_client = client.InstagramClient()
    insta_client.login()
    insta_client.verify_sms_code('+380634503781', '123123')


