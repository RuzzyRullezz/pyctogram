from pyctogram.instagram_client import client
from pyctogram.tests import account

if __name__ == '__main__':
    insta_client = client.InstagramClient(account.username, account.password)
    insta_client.login_v2()
    response = insta_client.get_user_story_feed(12032437331)
    items = response['reel']['items']
    response = insta_client.mark_media_seen(items)
    print(response)
