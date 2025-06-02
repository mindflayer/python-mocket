import asyncio
import glob
import json
import socket
import tempfile

import aiohttp
import pytest

from mocket import Mocketizer, async_mocketize
from mocket.mockhttp import Entry
from mocket.plugins.aiohttp_connector import MocketTCPConnector


def test_asyncio_record_replay():
    async def test_asyncio_connection():
        reader, writer = await asyncio.open_connection(
            host="google.com",
            port=80,
            family=socket.AF_INET,
            proto=socket.IPPROTO_TCP,
            ssl=None,
            server_hostname=None,
        )

        buf = "GET / HTTP/1.1\r\nHost: google.com\r\n\r\n"
        writer.write(buf.encode())
        await writer.drain()

        await reader.readline()
        writer.close()
        await writer.wait_closed()

    with tempfile.TemporaryDirectory() as temp_dir:
        with Mocketizer(truesocket_recording_dir=temp_dir):
            asyncio.run(test_asyncio_connection())

        files = glob.glob(f"{temp_dir}/*.json")
        assert len(files) == 1

        with open(files[0]) as f:
            responses = json.load(f)

        assert len(responses["google.com"]["80"].keys()) == 1


@pytest.mark.asyncio
@async_mocketize
async def test_aiohttp():
    """
    The alternative to using the custom `connector` would be importing
    `aiohttp` when Mocket is already in control (inside the decorated test).
    """

    url = "https://bar.foo/"
    data = {"message": "Hello"}

    Entry.single_register(
        Entry.GET,
        url,
        body=json.dumps(data),
        headers={"content-type": "application/json"},
    )

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=3), connector=MocketTCPConnector()
    ) as session, session.get(url) as response:
        response = await response.json()
        assert response == data
