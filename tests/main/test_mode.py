import pytest
import requests

from mocket import Mocketizer, mocketize
from mocket.exceptions import StrictMocketException


@mocketize(strict_mode=True)
def test_strict_mode_fails():
    url = "https://httpbin.org/ip"

    with pytest.raises(StrictMocketException):
        requests.get(url, headers={"Accept": "application/json"})


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_intermittent_strict_mode():
    url = "https://httpbin.org/ip"

    with Mocketizer(strict_mode=False):
        requests.get(url, headers={"Accept": "application/json"})

    with Mocketizer(strict_mode=True):
        with pytest.raises(StrictMocketException):
            requests.get(url, headers={"Accept": "application/json"})

    with Mocketizer(strict_mode=False):
        requests.get(url, headers={"Accept": "application/json"})
