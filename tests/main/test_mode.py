import pytest
import requests

from mocket import Mocketizer, mocketize
from mocket.exceptions import StrictMocketException
from mocket.mockhttp import Entry, Response
from mocket.utils import MocketMode


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
Mocket tried to use the real `socket` module while STRICT mode was active.
Registered entries:
  ('httpbin.local', 80):
    Entry(method='GET', schema='http', location=('httpbin.local', 80), path='/user.agent', query='')
""".strip()
        )


def test_strict_mode_false_with_allowed_hosts():
    with pytest.raises(ValueError):
        Mocketizer(strict_mode=False, strict_mode_allowed=["foobar.local"])


def test_strict_mode_false_always_allowed():
    with Mocketizer(strict_mode=False):
        assert MocketMode().is_allowed("foobar.com")
        assert MocketMode().is_allowed(("foobar.com", 443))
