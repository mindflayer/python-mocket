from setuptools import setup, find_packages, os
from io import open

# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
for m in ('multiprocessing', 'billiard'):
    try:
        __import__(m)
    except ImportError:
        pass

dev_requires = []
install_requires = open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).read()
tests_require = open(os.path.join(os.path.dirname(__file__), 'test_requirements.txt')).read()

setup(
    name='mocket',
    version='1.5.0',
    # author='Andrea de Marco, Giorgio Salluzzo',
    author='Giorgio Salluzzo',
    # author_email='24erre@gmail.com, giorgio.salluzzo@gmail.com',
    author_email='giorgio.salluzzo@gmail.com',
    url='https://github.com/mindflayer/python-mocket',
    description='Socket Mock Framework',
    long_description=open('README.rst', encoding='utf-8').read(),
    packages=find_packages(exclude=('tests', 'tests35')),
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
        'dev': dev_requires,
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
