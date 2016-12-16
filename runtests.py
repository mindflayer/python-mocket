#!/usr/bin/env python
import sys


def runtests(args=None):
    import pytest

    if not args:
        args = []

    major, minor = sys.version_info[:2]

    python35 = False

    if major == 3 and minor >= 5:
        python35 = True

        import pip
        pip.main(['install', 'aiohttp'])

    if not any(a for a in args[1:] if not a.startswith('-')):
        args.append('tests')
        args.append('mocket')

        if python35:
            args.append('tests35')

    sys.exit(pytest.main(args))


if __name__ == '__main__':
    runtests(sys.argv)
