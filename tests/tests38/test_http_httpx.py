import json
from unittest import IsolatedAsyncioTestCase

import httpx

from mocket.plugins.httpretty import HTTPretty, async_httprettified


class HttpxEntryTestCase(IsolatedAsyncioTestCase):
    target_url = "http://httpbin.local/ip"

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


class HttpxHttpsEntryTestCase(IsolatedAsyncioTestCase):
    target_url = "https://httpbin.local/ip"

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
