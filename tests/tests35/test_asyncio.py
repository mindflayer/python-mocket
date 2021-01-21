import asyncio
import json
from unittest import TestCase
import socket

from mocket.mocket import Mocket, mocketize


class AsyncIoEnterTestCase(TestCase):
    def test_asyncio_record_replay(self):
        async def test_asyncio_connection():
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
            return r
    
        mock_out = b'HTTP/1.1 301 Moved Permanently\r\n'
        # This enables mocket to record the response
        Mocket.enable("test_asyncio_record", ".")

        out = asyncio.run(test_asyncio_connection())
        assert out == mock_out

