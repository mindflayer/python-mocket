#!/usr/bin/env python
import sys


def runtests(args=None):
    import pytest
    import pip

    if not args:
        args = []

    major, minor = sys.version_info[:2]

    python27 = False
    python35 = False

    # gevent not available on Python 2.6
    if major >= 2 and minor > 6:

        python27 = True

        pip.main(['install', 'gevent'])

    # aiohttp available on Python >=3.5
    if major == 3 and minor >= 5:
        python35 = True

        pip.main(['install', 'aiohttp'])

    if not any(a for a in args[1:] if not a.startswith('-')):
        args.append('tests')
        args.append('mocket')

        if python27:
            args.append('tests27')

        if python35:
            args.append('tests35')

    sys.exit(pytest.main(args))


if __name__ == '__main__':
    runtests(sys.argv)
