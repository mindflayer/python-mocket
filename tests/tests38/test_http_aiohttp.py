import asyncio
import json
from unittest import IsolatedAsyncioTestCase

import aiohttp
import async_timeout

from mocket.mocket import Mocket, async_mocketize
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import HTTPretty, httprettified


class AioHttpEntryTestCase(IsolatedAsyncioTestCase):
    @async_mocketize
    async def test_http_session(self):
        url = 'http://httpbin.org/ip'
        body = "asd" * 100
        Entry.single_register(Entry.GET, url, body=body, status=404)
        Entry.single_register(Entry.POST, url, body=body*2, status=201)

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(3):
                async with session.get(url) as get_response:
                    assert get_response.status == 404
                    assert await get_response.text() == body

            with async_timeout.timeout(3):
                async with session.post(url, data=body * 6) as post_response:
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2
                    assert Mocket.last_request().method == 'POST'
                    assert Mocket.last_request().body == body * 6

        self.assertEqual(len(Mocket._requests), 2)

    @async_mocketize
    async def test_https_session(self):
        url = 'https://httpbin.org/ip'
        body = "asd" * 100
        Entry.single_register(Entry.GET, url, body=body, status=404)
        Entry.single_register(Entry.POST, url, body=body*2, status=201)

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(3):
                async with session.get(url) as get_response:
                    assert get_response.status == 404
                    assert await get_response.text() == body

            with async_timeout.timeout(3):
                async with session.post(url, data=body * 6) as post_response:
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2

        self.assertEqual(len(Mocket._requests), 2)

    # @httprettified
    # def test_httprettish_session(self):
    #     url = 'https://httpbin.org/ip'
    #     HTTPretty.register_uri(
    #         HTTPretty.GET,
    #         url,
    #         body=json.dumps(dict(origin='127.0.0.1')),
    #     )
    #
    #     async def main(l):
    #         async with aiohttp.ClientSession(loop=l) as session:
    #             with async_timeout.timeout(3):
    #                 async with session.get(url) as get_response:
    #                     assert get_response.status == 200
    #                     assert await get_response.text() == '{"origin": "127.0.0.1"}'
    #     loop = asyncio.get_event_loop()
    #     loop.set_debug(True)
    #     loop.run_until_complete(main(loop))
