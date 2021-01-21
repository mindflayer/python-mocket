import asyncio
import glob
import io
import json
import shutil
import socket
import tempfile
from unittest import TestCase

from mocket.mocket import mocketize


class AsyncIoRecordTestCase(TestCase):
    temp_dir = tempfile.mkdtemp()

    @mocketize(truesocket_recording_dir=temp_dir)
    def test_asyncio_record_replay(self):
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

        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.run_until_complete(test_asyncio_connection())

        files = glob.glob(f"{self.temp_dir}/*.json")
        self.assertEqual(len(files), 1)

        with io.open(files[0]) as f:
            responses = json.load(f)

        self.assertEqual(len(responses["google.com"]["80"].keys()), 1)

        shutil.rmtree(self.temp_dir)
