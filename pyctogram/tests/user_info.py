from pyctogram.instagram_client import client, web
from pyctogram.tests import account

if __name__ == '__main__':
    user_info = web.get_user_info('gubernatar')
    print(user_info)
