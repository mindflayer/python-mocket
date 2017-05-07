import aiohttp
import asyncio
from unittest import TestCase

from mocket.mocket import mocketize
from mocket.mockhttp import Entry


class AioHttpEntryTestCase(TestCase):
    @mocketize
    def test_session(self):
        url = 'https://httpbin.org/ip'
        body = "asd" * 100
        Entry.single_register(Entry.GET, url, body=body, status=404)
        Entry.single_register(Entry.POST, url, body=body*2, status=201)

        async def main(l):
            async with aiohttp.ClientSession(loop=l) as session:
                async with session.get(url) as get_response:
                    assert get_response.status == 404
                    assert await get_response.text() == body

                async with session.post(url, data=body*6) as post_response:
                    assert post_response.status == 201
                    assert await post_response.text() == body*2

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(loop))
