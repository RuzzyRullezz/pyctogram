from setuptools import setup, find_packages

import pyctogram

setup(
    name='pyctogtam',
    version=pyctogram.__version__,
    author='Ruzzy Rullezz',
    author_email='ruslan@lemimi.ru',
    packages=find_packages(),
    package_dir={'pyctogram': 'pyctogram'},
    package_data={
        'pyctogtam': ['test/data/*']
    },
    install_requires=[
        'requests',
        'pytz',
        'pillow',
        'av',
    ],
)
