from __future__ import unicode_literals

import io
import os
import socket
from unittest import TestCase
from unittest.mock import patch

import httpx
import psutil
import pytest

from mocket import Mocket, MocketEntry, Mocketizer, mocketize
from mocket.compat import encode_to_bytes


class MocketTestCase(TestCase):
    def setUp(self):
        Mocket.reset()

    def test_lastrequest(self):
        self.assertEqual(Mocket.last_request(), None)
        Mocket.request_list().extend([1, 2, 3])
        self.assertEqual(Mocket.last_request(), 3)

    def test_reset(self):
        Mocket.request_list().extend([1, 2, 3])
        self.assertEqual(Mocket.request_list(), [1, 2, 3])
        Mocket.reset()
        self.assertEqual(Mocket.request_list(), [])

    def test_has_requests(self):
        Mocket.request_list().extend([1, 2, 3])
        self.assertTrue(Mocket.has_requests())
        Mocket.reset()
        self.assertFalse(Mocket.has_requests())

    def test_gethostname(self):
        hostname = socket.gethostname()
        Mocket.enable()
        self.assertEqual(socket.gethostname(), "localhost")
        Mocket.disable()
        self.assertEqual(socket.gethostname(), hostname)

    def test_gethostbyname(self):
        host = socket.gethostbyname("localhost")
        Mocket.enable()
        self.assertEqual(socket.gethostbyname("localhost"), "127.0.0.1")
        Mocket.disable()
        self.assertEqual(socket.gethostbyname("localhost"), host)

    def test_register(self):
        entry_1 = MocketEntry(("localhost", 80), True)
        entry_2 = MocketEntry(("localhost", 80), True)
        entry_3 = MocketEntry(("localhost", 8080), True)
        Mocket.register(entry_1, entry_2, entry_3)
        self.assertEqual(
            Mocket._entries,
            {
                ("localhost", 80): [entry_1, entry_2],
                ("localhost", 8080): [entry_3],
            },
        )

    def test_collect(self):
        request = "GET /get/p/?b=2&a=1 HTTP/1.1\r\nAccept-Encoding: identity\r\nHost: testme.org\r\nConnection: close\r\nUser-Agent: Python-urllib/2.6\r\n\r\n"
        Mocket.collect(request)
        self.assertEqual(Mocket.last_request(), request)
        self.assertEqual(Mocket.request_list(), [request])

    def test_remove_last(self):
        Mocket._requests = [1, 2]
        Mocket.remove_last_request()
        self.assertEqual(Mocket.request_list(), [1])

    def test_remove_last_empty(self):
        Mocket.remove_last_request()
        self.assertEqual(Mocket.request_list(), [])

    def test_getentry(self):
        entry = MocketEntry(("localhost", 80), True)
        Mocket.register(entry)
        self.assertEqual(Mocket.get_entry("localhost", 80, True), entry)

    def test_getresponse(self):
        entry = MocketEntry(("localhost", 8080), ["Show me.\r\n"])
        self.assertEqual(entry.get_response(), encode_to_bytes("Show me.\r\n"))

    def test_empty_getresponse(self):
        entry = MocketEntry(("localhost", 8080), [])
        self.assertEqual(entry.get_response(), encode_to_bytes(""))

    def test_raise_exception(self):
        entry = MocketEntry(("localhost", 8080), [IOError()])

        with self.assertRaises(IOError):
            entry.get_response()

    def test_collect_last_request(self):
        addr = ("localhost", 80)

        entry = MocketEntry(addr, True)
        Mocket.register(entry)
        with Mocketizer():
            _so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _so.connect(addr)
            _so.sendall(b"data\r\n")
            _so.close()
            self.assertEqual(Mocket.last_request(), b"data\r\n")

    def test_subsequent_recv_requests_have_correct_length(self):
        addr = ("localhost", 80)
        Mocket.register(MocketEntry(addr, [b"Long payload", b"Short"]))
        with Mocketizer():
            _so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _so.connect(addr)
            _so.sendall(b"first\r\n")
            self.assertEqual(_so.recv(4096), b"Long payload")
            _so.sendall(b"second\r\n")
            self.assertEqual(_so.recv(4096), b"Short")
            _so.close()

    def test_recv_into(self):
        addr = ("localhost", 80)
        Mocket.register(MocketEntry(addr, [b"Long payload", b"Short"]))
        buffer = io.BytesIO()
        with Mocketizer():
            _so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _so.connect(addr)
            _so.sendall(b"first\r\n")
            self.assertEqual(_so.recv_into(buffer, 4096), 12)
            _so.sendall(b"second\r\n")
            self.assertEqual(_so.recv_into(buffer), 5)
            _so.close()
        buffer.seek(0)
        assert buffer.read() == b"Long payloadShort"

    def test_makefile(self):
        addr = ("localhost", 80)
        Mocket.register(MocketEntry(addr, ["Show me.\r\n"]))
        with Mocketizer():
            _so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _so.connect(addr)
            fp = _so.makefile("rb")
            _so.sendall(encode_to_bytes("...\r\n"))
            self.assertEqual(fp.read().strip(), encode_to_bytes("Show me."))
            self.assertEqual(len(Mocket.request_list()), 1)

    @pytest.mark.skipif(
        'os.getenv("SKIP_TRUE_HTTP", False) or os.getenv("SKIP_TRUE_REDIS", False)'
    )
    def test_multiple_socket_connections(self):
        redis_addr = ("localhost", 6379)
        httpbin_addr = ("localhost", 80)

        redis_buffer = io.BytesIO()
        httpbin_buffer = io.BytesIO()

        with Mocketizer():
            redis_so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            redis_so.connect(redis_addr)

            httpbin_so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            httpbin_so.connect(httpbin_addr)

            # Creating another socket that connects to a different address
            # should not cause the first connection to go awry.
            redis_so.sendall(b"ping\r\n")
            redis_so.recv_into(redis_buffer)

            httpbin_so.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            httpbin_so.recv_into(httpbin_buffer)

        redis_buffer.seek(0)
        assert redis_buffer.read() == b"+PONG\r\n"
        httpbin_buffer.seek(0)
        assert httpbin_buffer.read().startswith(b"HTTP/1.1 200 OK\r\n")

    def test_socket_as_context_manager(self):
        addr = ("localhost", 80)
        Mocket.register(MocketEntry(addr, ["Show me.\r\n"]))
        with Mocketizer():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _so:
                _so.connect(addr)
                _so.sendall(encode_to_bytes("Whatever..."))
                data = _so.recv(4096)
                self.assertEqual(data, encode_to_bytes("Show me.\r\n"))
                self.assertEqual(str(_so), "(MocketSocket)(family=2 type=1 protocol=0)")


class MocketizeTestCase(TestCase):
    def mocketize_setup(self):
        pass

    def mocketize_teardown(self):
        pass

    @mocketize
    def test_gethostname(self):
        self.assertEqual(socket.gethostname(), "localhost")


@mocketize
def test_mocketize_outside_a_test_class():
    assert 2 == 2


@pytest.fixture
def two():
    return 2


@mocketize
def test_mocketize_with_fixture(two):
    assert 2 == two


@mocketize
@patch("os.getcwd")
def test_patch(
    method_patch,
):
    method_patch.return_value = "foo"
    assert os.getcwd() == "foo"


@pytest.mark.skipif(not psutil.POSIX, reason="Uses a POSIX-only API to test")
@pytest.mark.asyncio
async def test_no_dangling_fds():
    url = "http://httpbin.local/ip"

    proc = psutil.Process(os.getpid())

    prev_num_fds = proc.num_fds()

    async with Mocketizer(strict_mode=False):
        async with httpx.AsyncClient() as client:
            await client.get(url)

    assert proc.num_fds() == prev_num_fds
