from setuptools import setup, find_packages

import pyctogram

setup(
    name='telegram_log',
    version=pyctogram.__version__,
    author='Ruzzy Rullezz',
    author_email='ruslan@lemimi.ru',
    packages=find_packages(),
    package_dir={'pyctogram': 'pyctogram'},
    install_requires=[
        'requests',
        'pytz',
        'pillow',
    ],
)
