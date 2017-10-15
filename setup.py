import sys
from io import open

from setuptools import setup, find_packages, os


major, minor = sys.version_info[:2]

install_requires = open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).readlines()
tests_requires = open(os.path.join(os.path.dirname(__file__), 'test_requirements.txt')).readlines()

pook_requires = ['pook>=0.2.1']
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


def read_version(package):
    init_path = os.path.join(package, '__init__.py')
    with open(init_path, 'r') as fd:
        for line in fd:
            if line.startswith('__version__ = '):
                return line.split()[-1].strip().strip("'")

package_name = 'mocket'

# Get package current version
version = read_version(package_name)


setup(
    name=package_name,
    version=read_version(package_name),
    author='Giorgio Salluzzo',
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
