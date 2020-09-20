import sys


def pytest_ignore_collect(path):
    if sys.version_info[0] < 3 and "async_" in str(path):
        return True
    return False
