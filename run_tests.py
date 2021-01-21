#!/usr/bin/env python
import sys


def main(args=None):
    import pytest

    if not args:
        args = []

    major, minor = sys.version_info[:2]

    if not any(a for a in args[1:] if not a.startswith("-")):
        args.append("tests/main")
        args.append("mocket")
        args.append("tests/tests35")

        if major == 3 and minor >= 7:
            args.append("tests/tests37")

        if major == 3 and minor >= 8:
            args.append("tests/tests38")

    sys.exit(pytest.main(args))


if __name__ == "__main__":
    main(sys.argv)
