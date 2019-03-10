import os
from pyctogram.instagram_client import client
from pyctogram.tests import account

if __name__ == '__main__':
    insta_client = client.InstagramClient(account.username, account.password)
    insta_client.login()
    image_path = os.path.join(os.path.dirname(__file__), 'data', 'example.jpg')
    response = insta_client.upload_photo(image_path)
    print(response)
