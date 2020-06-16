import pook
import requests

from mocket.plugins.pook_mock_engine import MocketEngine

pook.set_mock_engine(MocketEngine)


@pook.on
def test_pook_engine():

    url = "http://twitter.com/api/1/foobar"
    status = 404
    response_json = {"error": "foo"}

    mock = pook.get(
        url,
        headers={"content-type": "application/json"},
        reply=status,
        response_json=response_json,
    )
    mock.persist()

    requests.get(url)
    assert mock.calls == 1

    resp = requests.get(url)
    assert resp.status_code == status
    assert resp.json() == response_json
    assert mock.calls == 2
