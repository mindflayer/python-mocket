import asyncio
import json
from unittest import TestCase
import socket
import io

from mocket.mocket import Mocket, mocketize


class AsyncIoRecordTestCase(TestCase):
    def test_asyncio_record_replay(self):
        async def test_asyncio_connection():
            mock_out = b'HTTP/1.1 301 Moved Permanently\r\n'
            reader, writer = await asyncio.open_connection(
                host='google.com',
                port=80,
                family=socket.AF_INET,
                proto=socket.IPPROTO_TCP,
                ssl=None,
                server_hostname=None,
            )

            buf = 'GET / HTTP/1.1\r\nHost: google.com\r\n\r\n'
            writer.write(buf.encode())
            await writer.drain()

            r = await reader.readline()
            writer.close()
            await writer.wait_closed()
    
        mock_out = b'HTTP/1.1 301 Moved Permanently\r\n'

        test_name = 'test_asyncio_record'
        # This enables mocket to record the response
        Mocket.enable(test_name, ".")

        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.run_until_complete(test_asyncio_connection())

        dump_filename = f'./{test_name}.json'
        with io.open(dump_filename) as f:
            responses = json.load(f)

        assert len(responses["google.com"]["80"].keys()) == 1
