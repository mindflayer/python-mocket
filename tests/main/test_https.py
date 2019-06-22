import io
import json
import os
import tempfile

import pytest
import requests
from tests import urlopen

from mocket import Mocket, mocketize, Mocketizer
from mocket.mockhttp import Entry


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
        headers={'content-type': 'application/json'})

    mocked_response = requests.get(url_to_mock).json()
    assert response == mocked_response

    mocked_response = json.loads(urlopen(url_to_mock).read().decode('utf-8'))
    assert response == mocked_response


recording_directory = tempfile.mkdtemp()


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
@mocketize(truesocket_recording_dir=recording_directory)
def test_truesendall_with_recording_https():
    url = 'https://mockbin.com/ip'

    requests.get(url, headers={"Accept": "application/json"})
    resp = requests.get(url, headers={"Accept": "application/json"})
    print(resp.content)
    assert resp.status_code == 200

    dump_filename = os.path.join(
        Mocket.get_truesocket_recording_dir(),
        Mocket.get_namespace() + '.json',
    )
    with io.open(dump_filename) as f:
        responses = json.load(f)

    assert len(responses['mockbin.com']['443'].keys()) == 1


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_truesendall_after_mocket_session():
    Mocket.enable()
    Mocket.disable()

    url = 'https://mockbin.com/ip'
    resp = requests.get(url)
    assert resp.status_code == 200


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_real_request_session():
    session = requests.Session()

    url1 = 'https://mockbin.com/ip'
    url2 = 'http://mockbin.com/request'

    with Mocketizer():
        assert len(session.get(url1).content) < len(session.get(url2).content)
