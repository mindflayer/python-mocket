import io
import json
import os
import tempfile
from urllib.request import urlopen

import pytest
import requests

from mocket import Mocket, Mocketizer, mocketize
from mocket.mockhttp import Entry


@pytest.fixture
def url_to_mock():
    return "https://httpbin.org/ip"


@pytest.fixture
def response():
    return {
        "integer": 1,
        "string": "asd",
        "boolean": False,
    }


@mocketize
def test_json(response):
    url_to_mock = "https://testme.org/json"

    Entry.single_register(
        Entry.GET,
        url_to_mock,
        body=json.dumps(response),
        headers={"content-type": "application/json"},
    )

    mocked_response = requests.get(url_to_mock).json()
    assert response == mocked_response

    mocked_response = json.loads(urlopen(url_to_mock).read().decode("utf-8"))
    assert response == mocked_response


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_truesendall_with_recording_https(url_to_mock):
    with tempfile.TemporaryDirectory() as temp_dir:
        with Mocketizer(truesocket_recording_dir=temp_dir):
            requests.get(url_to_mock, headers={"Accept": "application/json"})
            resp = requests.get(url_to_mock, headers={"Accept": "application/json"})
            assert resp.status_code == 200

            dump_filename = os.path.join(
                Mocket.get_truesocket_recording_dir(),
                Mocket.get_namespace() + ".json",
            )
            with io.open(dump_filename) as f:
                responses = json.load(f)

    assert len(responses["httpbin.org"]["443"].keys()) == 1


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_truesendall_after_mocket_session(url_to_mock):
    Mocket.enable()
    Mocket.disable()

    resp = requests.get(url_to_mock)
    assert resp.status_code == 200


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
def test_real_request_session(url_to_mock):
    session = requests.Session()

    url_to_compare = "http://httpbin.org/headers"

    with Mocketizer():
        assert len(session.get(url_to_mock).content) < len(
            session.get(url_to_compare).content
        )
