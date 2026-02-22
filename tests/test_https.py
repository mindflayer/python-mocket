import json
import os
import tempfile
from urllib.request import urlopen

import pytest
import requests

from mocket import Mocket, Mocketizer, mocketize
from mocket.mockhttp import Entry  # noqa - test retrocompatibility


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
@pytest.mark.xfail(reason="Service down or blocking GitHub actions IPs")
def test_truesendall_with_recording_https(url_to_mock):
    with tempfile.TemporaryDirectory() as temp_dir, Mocketizer(
        truesocket_recording_dir=temp_dir
    ):
        requests.get(url_to_mock, headers={"Accept": "application/json"})
        resp = requests.get(url_to_mock, headers={"Accept": "application/json"})
        assert resp.status_code == 200

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(),
            Mocket.get_namespace() + ".json",
        )
        with open(dump_filename) as f:
            responses = json.load(f)

    assert len(responses["httpbin.org"]["443"].keys()) == 1


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
@pytest.mark.xfail(reason="Service down or blocking GitHub actions IPs")
def test_truesendall_after_mocket_session(url_to_mock):
    Mocket.enable()
    Mocket.disable()

    resp = requests.get(url_to_mock)
    assert resp.status_code == 200


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
@pytest.mark.xfail(reason="Service down or blocking GitHub actions IPs")
def test_real_request_session(url_to_mock):
    session = requests.Session()

    url_to_compare = "http://httpbin.org/headers"

    with Mocketizer():
        assert len(session.get(url_to_mock).content) < len(
            session.get(url_to_compare).content
        )


@mocketize
def test_raise_exception_from_single_register():
    url = "https://github.com/fluidicon.png"
    Entry.single_register(Entry.GET, url, exception=OSError())
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(url)


@mocketize
def test_can_handle():
    Entry.single_register(
        Entry.GET,
        "https://httpbin.org",
        body=json.dumps({"message": "Nope... not this time!"}),
        headers={"content-type": "application/json"},
        can_handle_fun=lambda path, qs_dict: path == "/ip" and qs_dict,
    )
    Entry.single_register(
        Entry.GET,
        "https://httpbin.org",
        body=json.dumps({"message": "There you go!"}),
        headers={"content-type": "application/json"},
        can_handle_fun=lambda path, qs_dict: path == "/ip" and not qs_dict,
    )
    resp = requests.get("https://httpbin.org/ip")
    assert resp.status_code == 200
    assert resp.json() == {"message": "There you go!"}
