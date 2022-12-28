import asyncio
import glob
import io
import json
import socket
import tempfile

from mocket import Mocketizer


def test_asyncio_record_replay(event_loop):
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
            event_loop.run_until_complete(test_asyncio_connection())

        files = glob.glob(f"{temp_dir}/*.json")
        assert len(files) == 1

        with io.open(files[0]) as f:
            responses = json.load(f)

        assert len(responses["google.com"]["80"].keys()) == 1
