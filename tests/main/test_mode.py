import pytest
import requests

from mocket import Mocketizer, mocketize
from mocket.exceptions import StrictMocketException
from mocket.mockhttp import Entry, Response


@mocketize(strict_mode=True)
def test_strict_mode_fails():
    url = "http://httpbin.local/ip"

    with pytest.raises(StrictMocketException):
        requests.get(url)


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_intermittent_strict_mode():
    url = "http://httpbin.local/ip"

    with Mocketizer(strict_mode=False):
        requests.get(url)

    with Mocketizer(strict_mode=True):
        with pytest.raises(StrictMocketException):
            requests.get(url)

    with Mocketizer(strict_mode=False):
        requests.get(url)


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_strict_mode_exceptions():
    url = "http://httpbin.local/ip"

    with Mocketizer(strict_mode=True, strict_mode_allowed=["httpbin.local"]):
        requests.get(url)

    with Mocketizer(strict_mode=True, strict_mode_allowed=[("httpbin.local", 80)]):
        requests.get(url)


def test_strict_mode_error_message():
    url = "http://httpbin.local/ip"

    Entry.register(Entry.GET, "http://httpbin.local/user.agent", Response(status=404))

    with Mocketizer(strict_mode=True):
        with pytest.raises(StrictMocketException) as exc_info:
            requests.get(url)
        assert (
            str(exc_info.value)
            == """
Mocket tried to use the real `socket` module while strict mode is active.
Registered entries:
  ('httpbin.local', 80):
    Entry(method='GET', schema='http', location=('httpbin.local', 80), path='/user.agent', query='')
""".strip()
        )
