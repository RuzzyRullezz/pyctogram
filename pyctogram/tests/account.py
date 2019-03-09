import os
import getpass

username = os.environ.get('INSTA_TEST_NAME') or input("Enter username:")
password = os.environ.get('INSTA_TEST_PASS') or getpass.getpass("Enter password:")

user_id = 295116275