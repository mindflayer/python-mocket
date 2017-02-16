import os
import io
import json
import tempfile

import requests
import pytest

from mocket import mocketize, Mocket
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


recording_directory = tempfile.mkdtemp()


@mocketize(truesocket_recording_dir=recording_directory)
def test_truesendall_with_recording_https():
    url = 'https://httpbin.org/ip'

    requests.get(url)
    resp = requests.get(url)
    assert resp.status_code == 200

    dump_filename = os.path.join(
        Mocket.get_truesocket_recording_dir(),
        Mocket.get_namespace() + '.json',
    )
    with io.open(dump_filename) as f:
        responses = json.load(f)

    assert len(responses['httpbin.org']['443'].keys()) == 1
