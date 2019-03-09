from pyctogram.instagram_client import client
from pyctogram.tests import account

if __name__ == '__main__':
    insta_client = client.InstagramClient(account.username, account.password)
    insta_client.login()
    last_media = insta_client.get_last_media_id(account.user_id)
    response = insta_client.comment(last_media['id'], 'WOW')
    print(response)
