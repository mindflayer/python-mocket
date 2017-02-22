import sys
from io import open

from setuptools import setup, find_packages, os

major, minor = sys.version_info[:2]

# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
for m in ('multiprocessing', 'billiard'):
    try:
        __import__(m)
    except ImportError:
        pass

install_requires = open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).readlines()
tests_requires = open(os.path.join(os.path.dirname(__file__), 'test_requirements.txt')).readlines()
pook_requires = ['pook>=0.1.13']

exclude_packages = ['tests', 'tests35', 'mocket.plugins.pook']

if major > 2 or (major == 2 and minor > 6):
    # pook does not support Python 2.6
    exclude = exclude_packages[:-1]
    tests_requires += pook_requires
    # last flake8 version
    tests_requires.append('flake8')
else:
    # flake8 version >=3 does not support Python 2.6
    tests_requires.append('flake8<3.0')

setup(
    name='mocket',
    version='1.7.6',
    # author='Andrea de Marco, Giorgio Salluzzo',
    author='Giorgio Salluzzo',
    # author_email='24erre@gmail.com, giorgio.salluzzo@gmail.com',
    author_email='giorgio.salluzzo@gmail.com',
    url='https://github.com/mindflayer/python-mocket',
    description='Socket Mock Framework - for all kinds of socket animals, web-clients included - \
        with gevent/asyncio/SSL support',
    long_description=open('README.rst', encoding='utf-8').read(),
    packages=find_packages(exclude=exclude_packages),
    install_requires=install_requires,
    extras_require={
        'tests': tests_requires,
        'dev': [],
        'pook': pook_requires,  # plugins version supporting mocket.plugins.pook.MocketEngine
    },
    test_suite='runtests.runtests',
    license='BSD',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: BSD License',
    ],
)
