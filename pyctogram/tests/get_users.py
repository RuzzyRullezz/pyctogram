from pyctogram.instagram_client.relations import base
from pyctogram.tests import account

if __name__ == '__main__':
    victim = 'sova_timofei'
    for user in base.get_users(account.username, account.password, victim):
        print(user)
