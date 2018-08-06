import json

import asks
import curio
from unittest import TestCase

from mocket.mocket import mocketize, Mocket
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import HTTPretty, httprettified


class AsksEntryTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        asks.init('curio')

    def test_http_unmocked(self):
        url = 'http://httpbin.org/ip'
        response_received = False

        async def main():
            nonlocal response_received
            async with asks.Session() as session:
                async with curio.timeout_after(3):
                    get_response = await session.get(url)
                    assert get_response.status_code == 200
                    response_received = True

        curio.run(main)
        self.assertTrue(response_received)

    @mocketize
    def test_http_session(self):
        url = 'http://httpbin.org/ip'
        body = "asd" * 100
        Entry.single_register(Entry.GET, url, body=body, status=404)
        Entry.single_register(Entry.POST, url, body=body*2, status=201)

        async def main():
            async with asks.Session() as session:
                async with curio.timeout_after(300):
                    get_response = await session.get(url)
                    assert get_response.status == 404
                    assert await get_response.text() == body

                async with curio.timeout_after(3):
                    post_response = await session.post(url, data=body * 6)
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2
                    assert Mocket.last_request().method == 'POST'
                    assert Mocket.last_request().body == body * 6

        curio.run(main)
        self.assertEqual(len(Mocket._requests), 2)

    @mocketize
    def test_https_session(self):
        url = 'https://httpbin.org/ip'
        body = "asd" * 100
        Entry.single_register(Entry.GET, url, body=body, status=404)
        Entry.single_register(Entry.POST, url, body=body*2, status=201)

        async def main():
            async with asks.Session() as session:
                async with curio.timeout_after(3):
                    get_response = await session.get(url)
                    assert get_response.status == 404
                    assert await get_response.text() == body

                async with curio.timeout_after(3):
                    post_response = await session.post(url, data=body * 6)
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2

        curio.run(main)
        self.assertEqual(len(Mocket._requests), 2)

    @httprettified
    def test_httprettish_session(self):
        url = 'https://httpbin.org/ip'
        HTTPretty.register_uri(
            HTTPretty.GET,
            url,
            body=json.dumps(dict(origin='127.0.0.1')),
        )

        async def main():
            async with asks.Session() as session:
                async with curio.timeout_after(3):
                    get_response = await session.get(url)
                    assert get_response.status == 200
                    assert await get_response.text() == '{"origin": "127.0.0.1"}'
        curio.run(main)
