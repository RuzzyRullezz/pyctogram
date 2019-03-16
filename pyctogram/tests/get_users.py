from pyctogram.instagram_client.relations import base
from pyctogram.tests import account

if __name__ == '__main__':
    victim = 'sova_timofei'
    proxies = None
    counter = 0
    for user in base.get_users(account.username, account.password, victim, proxies=proxies):
        counter += 1
        print(counter)
        print(user)
