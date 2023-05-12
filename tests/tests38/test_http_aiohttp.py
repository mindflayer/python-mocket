import json
from unittest import IsolatedAsyncioTestCase

import aiohttp
import httpx
import pytest

from mocket.async_mocket import async_mocketize
from mocket.mocket import Mocket
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import HTTPretty, async_httprettified


class AioHttpEntryTestCase(IsolatedAsyncioTestCase):
    timeout = aiohttp.ClientTimeout(total=3)
    target_url = "http://httpbin.local/ip"

    @async_mocketize
    async def test_http_session(self):
        body = "asd" * 100
        Entry.single_register(Entry.GET, self.target_url, body=body, status=404)
        Entry.single_register(Entry.POST, self.target_url, body=body * 2, status=201)

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(self.target_url) as get_response:
                assert get_response.status == 404
                assert await get_response.text() == body

            async with session.post(self.target_url, data=body * 6) as post_response:
                assert post_response.status == 201
                assert await post_response.text() == body * 2
                assert Mocket.last_request().method == "POST"
                assert Mocket.last_request().body == body * 6

        self.assertEqual(len(Mocket.request_list()), 2)

    @async_mocketize
    async def test_https_session(self):
        body = "asd" * 100
        Entry.single_register(Entry.GET, self.target_url, body=body, status=404)
        Entry.single_register(Entry.POST, self.target_url, body=body * 2, status=201)

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(self.target_url) as get_response:
                assert get_response.status == 404
                assert await get_response.text() == body

            async with session.post(self.target_url, data=body * 6) as post_response:
                assert post_response.status == 201
                assert await post_response.text() == body * 2

        self.assertEqual(len(Mocket.request_list()), 2)

    @pytest.mark.xfail
    @async_httprettified
    async def test_httprettish_session(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            self.target_url,
            body=json.dumps(dict(origin="127.0.0.1")),
        )

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(self.target_url) as get_response:
                assert get_response.status == 200
                assert await get_response.text() == '{"origin": "127.0.0.1"}'

    @async_httprettified
    async def test_httprettish_httpx_session(self):
        expected_response = {"origin": "127.0.0.1"}

        HTTPretty.register_uri(
            HTTPretty.GET,
            self.target_url,
            body=json.dumps(expected_response),
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(self.target_url)
            assert response.status_code == 200
            assert response.json() == expected_response
