import asyncio
import json
from unittest import IsolatedAsyncioTestCase, TestCase

import pytest

from mocket.async_mocket import async_mocketize
from mocket.mocket import Mocket, Mocketizer, mocketize
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import HTTPretty, async_httprettified

try:
    import aiohttp

    ENABLE_TEST_CLASS = True
except ImportError:
    ENABLE_TEST_CLASS = False


if ENABLE_TEST_CLASS:

    class AioHttpEntryTestCase(TestCase):
        @mocketize
        def test_https_session(self):
            url = "https://httpbin.org/ip"
            body = "asd" * 100
            Entry.single_register(Entry.GET, url, body=body, status=404)
            Entry.single_register(Entry.POST, url, body=body * 2, status=201)

            async def main(l):
                async with aiohttp.ClientSession(
                    loop=l, timeout=aiohttp.ClientTimeout(total=3)
                ) as session:
                    async with session.get(url) as get_response:
                        assert get_response.status == 404
                        assert await get_response.text() == body

                    async with session.post(url, data=body * 6) as post_response:
                        assert post_response.status == 201
                        assert await post_response.text() == body * 2

            loop = asyncio.new_event_loop()
            loop.run_until_complete(main(loop))

    class AioHttpEntryAsyncTestCase(IsolatedAsyncioTestCase):
        timeout = aiohttp.ClientTimeout(total=3)
        target_url = "http://httpbin.local/ip"

        @async_mocketize
        async def test_http_session(self):
            body = "asd" * 100
            Entry.single_register(Entry.GET, self.target_url, body=body, status=404)
            Entry.single_register(
                Entry.POST, self.target_url, body=body * 2, status=201
            )

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.target_url) as get_response:
                    assert get_response.status == 404
                    assert await get_response.text() == body

                async with session.post(
                    self.target_url, data=body * 6
                ) as post_response:
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2
                    assert Mocket.last_request().method == "POST"
                    assert Mocket.last_request().body == body * 6

            self.assertEqual(len(Mocket.request_list()), 2)

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

    class AioHttpsEntryTestCase(IsolatedAsyncioTestCase):
        timeout = aiohttp.ClientTimeout(total=3)
        target_url = "https://httpbin.localhost/anything/"

        @async_mocketize
        async def test_https_session(self):
            body = "asd" * 100
            Entry.single_register(Entry.GET, self.target_url, body=body, status=404)
            Entry.single_register(
                Entry.POST, self.target_url, body=body * 2, status=201
            )

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.target_url) as get_response:
                    assert get_response.status == 404
                    assert await get_response.text() == body

                async with session.post(
                    self.target_url, data=body * 6
                ) as post_response:
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2

            self.assertEqual(len(Mocket.request_list()), 2)

        @async_mocketize
        async def test_no_verify(self):
            Entry.single_register(Entry.GET, self.target_url, status=404)

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.target_url, ssl=False) as get_response:
                    assert get_response.status == 404

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

        @pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
        async def test_mocked_https_request_after_unmocked_https_request(self):
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                response = await session.get(self.target_url + "real", ssl=False)
                assert response.status == 200

            async with Mocketizer(None):
                Entry.single_register(Entry.GET, self.target_url + "mocked", status=404)
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    response = await session.get(self.target_url + "mocked", ssl=False)
                    assert response.status == 404
                    self.assertEqual(len(Mocket.request_list()), 1)
