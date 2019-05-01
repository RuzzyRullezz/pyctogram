from setuptools import setup, find_packages

import pyctogram

setup(
    name='pyctogram',
    version=pyctogram.__version__,
    author='Ruzzy Rullezz',
    author_email='ruslan@lemimi.ru',
    packages=find_packages(),
    package_dir={'pyctogram': 'pyctogram'},
    package_data={
        'pyctogtam': ['pyctogram/tests/data/*']
    },
    install_requires=[
        'requests',
        'pytz',
        'pillow',
        'av',
        'gmqtt',
        'cython',
        'thriftpy',
        'python-dateutil',
    ],
)
