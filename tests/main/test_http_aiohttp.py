import json
import sys

import aiohttp
import pytest
from asgiref.sync import async_to_sync

from mocket.mocket import Mocket, mocketize
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import httprettified, httpretty

timeout = aiohttp.ClientTimeout(total=3)


@mocketize
def test_http_session(event_loop):
    url = "http://httpbin.org/ip"
    body = "asd" * 100
    Entry.single_register(Entry.GET, url, body=body, status=404)
    Entry.single_register(Entry.POST, url, body=body * 2, status=201)

    @async_to_sync
    async def perform_aiohttp_transactions():
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as get_response:
                assert get_response.status == 404
                assert await get_response.text() == body

            async with session.post(url, data=body * 6) as post_response:
                assert post_response.status == 201
                assert await post_response.text() == body * 2
                assert Mocket.last_request().method == "POST"
                assert Mocket.last_request().body == body * 6

    perform_aiohttp_transactions()
    assert len(Mocket.request_list()) == 2


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="Failing with Python 3.11")
@mocketize
def test_https_session(event_loop):
    url = "https://httpbin.org/ip"
    body = "asd" * 100
    Entry.single_register(Entry.GET, url, body=body, status=404)
    Entry.single_register(Entry.POST, url, body=body * 2, status=201)

    @async_to_sync
    async def perform_aiohttp_transactions():
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as get_response:
                assert get_response.status == 404
                assert await get_response.text() == body

            async with session.post(url, data=body * 6) as post_response:
                assert post_response.status == 201
                assert await post_response.text() == body * 2

    perform_aiohttp_transactions()
    assert len(Mocket.request_list()) == 2


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="Failing with Python 3.11")
@httprettified
def test_httprettish_session(event_loop):
    url = "https://httpbin.org/ip"
    httpretty.register_uri(
        httpretty.GET,
        url,
        body=json.dumps(dict(origin="127.0.0.1")),
    )

    @async_to_sync
    async def perform_aiohttp_transactions():
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as get_response:
                assert get_response.status == 200
                assert await get_response.text() == '{"origin": "127.0.0.1"}'

    perform_aiohttp_transactions()
    assert len(httpretty.latest_requests) == 1
