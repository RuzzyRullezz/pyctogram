from pyctogram.instagram_client import client, web

if __name__ == '__main__':
    user_info = web.get_user_info('sova_timofei')
    print(user_info)
