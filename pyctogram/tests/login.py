from pyctogram.instagram_client import client

if __name__ == '__main__':
    insta_client = client.InstagramClient('ENTER YOUR LOGIN HERE', 'ENTER YOUR PASSWORD HERE')
    insta_client.login()
