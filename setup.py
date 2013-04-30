from setuptools import setup, find_packages

# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
for m in ('multiprocessing', 'billiard'):
    try:
        __import__(m)
    except ImportError:
        pass

dev_requires = [
    'flake8>=1.7.0,<2.0',
    'pytest-cov>=1.4',
]
tests_require = [
    'mock',
    'requests',
    'pytest',
]
install_requires = []

setup(
    name='python-mocket',
    version='0.1',
    author='Andrea de Marco',
    author_email='<24erre@gmail.com>',
    url='https://github.com/z4r/python-mocket',
    description='A Mock Socket Framework',
    long_description=open('README.rst').read(),
    package_dir={'': 'mocket'},
    packages=find_packages('mocket'),
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
        'dev': dev_requires,
    },
    test_suite='runtests.runtests',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Software Development :: Testing',
    ],
)
