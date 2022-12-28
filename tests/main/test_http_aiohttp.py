import json

import aiohttp

from mocket.mocket import Mocket, mocketize
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import HTTPretty, httprettified

timeout = aiohttp.ClientTimeout(total=3)


@mocketize
def test_http_session(event_loop):
    url = "http://httpbin.org/ip"
    body = "asd" * 100
    Entry.single_register(Entry.GET, url, body=body, status=404)
    Entry.single_register(Entry.POST, url, body=body * 2, status=201)

    async def main(_loop):
        async with aiohttp.ClientSession(loop=_loop, timeout=timeout) as session:
            async with session.get(url) as get_response:
                assert get_response.status == 404
                assert await get_response.text() == body

            async with session.post(url, data=body * 6) as post_response:
                assert post_response.status == 201
                assert await post_response.text() == body * 2
                assert Mocket.last_request().method == "POST"
                assert Mocket.last_request().body == body * 6

    event_loop.run_until_complete(main(event_loop))
    assert len(Mocket.request_list()) == 2


@mocketize
def test_https_session(event_loop):
    url = "https://httpbin.org/ip"
    body = "asd" * 100
    Entry.single_register(Entry.GET, url, body=body, status=404)
    Entry.single_register(Entry.POST, url, body=body * 2, status=201)

    async def main(_loop):
        async with aiohttp.ClientSession(loop=_loop, timeout=timeout) as session:
            async with session.get(url) as get_response:
                assert get_response.status == 404
                assert await get_response.text() == body

            async with session.post(url, data=body * 6) as post_response:
                assert post_response.status == 201
                assert await post_response.text() == body * 2

    event_loop.run_until_complete(main(event_loop))
    assert len(Mocket.request_list()) == 2


@httprettified
def test_httprettish_session(event_loop):
    url = "https://httpbin.org/ip"
    HTTPretty.register_uri(
        HTTPretty.GET,
        url,
        body=json.dumps(dict(origin="127.0.0.1")),
    )

    async def main(_loop):
        async with aiohttp.ClientSession(loop=_loop, timeout=timeout) as session:
            async with session.get(url) as get_response:
                assert get_response.status == 200
                assert await get_response.text() == '{"origin": "127.0.0.1"}'

    event_loop.run_until_complete(main(event_loop))
