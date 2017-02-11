import json

import requests
import pytest

from mocket.mocket import mocketize
from mocket.mockhttp import Entry
from tests import urlopen


@pytest.fixture
def response():
    return {
        "integer": 1,
        "string": "asd",
        "boolean": False,
    }


@mocketize
def test_json(response):
    url_to_mock = 'https://testme.org/json'

    Entry.single_register(
        Entry.GET,
        url_to_mock,
        body=json.dumps(response),
        headers={'content-type': 'application/json'}
    )

    mocked_response = requests.get(url_to_mock).json()
    assert response == mocked_response

    mocked_response = json.loads(urlopen(url_to_mock).read().decode('utf-8'))
    assert response == mocked_response
