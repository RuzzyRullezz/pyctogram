import os
import getpass

username = os.environ.get('INSTA_TEST_NAME', input("Enter username:"))
password = os.environ.get('INSTA_TEST_PASS', getpass.getpass("Enter password:"))