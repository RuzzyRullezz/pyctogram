from pyctogram.instagram_client import client, web
from pyctogram.tests import account

if __name__ == '__main__':
    logged_session = web.get_logged_session(account.username, account.password)
    web.session_logout(logged_session)
