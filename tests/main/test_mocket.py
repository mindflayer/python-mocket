from __future__ import unicode_literals
import socket
from unittest import TestCase

import pytest

from mocket import Mocket, mocketize, MocketEntry, Mocketizer
from mocket.compat import encode_to_bytes


class MocketTestCase(TestCase):
    def setUp(self):
        Mocket.reset()

    def test_lastrequest(self):
        self.assertEqual(Mocket.last_request(), None)
        Mocket._requests.extend([1, 2, 3])
        self.assertEqual(Mocket.last_request(), 3)

    def test_reset(self):
        Mocket._requests.extend([1, 2, 3])
        self.assertEqual(Mocket._requests, [1, 2, 3])
        Mocket.reset()
        self.assertEqual(Mocket._requests, [])

    def test_gethostname(self):
        hostname = socket.gethostname()
        Mocket.enable()
        self.assertEqual(socket.gethostname(), 'localhost')
        Mocket.disable()
        self.assertEqual(socket.gethostname(), hostname)

    def test_gethostbyname(self):
        host = socket.gethostbyname('localhost')
        Mocket.enable()
        self.assertEqual(socket.gethostbyname('localhost'), '127.0.0.1')
        Mocket.disable()
        self.assertEqual(socket.gethostbyname('localhost'), host)

    def test_register(self):
        entry_1 = MocketEntry(('localhost', 80), True)
        entry_2 = MocketEntry(('localhost', 80), True)
        entry_3 = MocketEntry(('localhost', 8080), True)
        Mocket.register(entry_1, entry_2, entry_3)
        self.assertEqual(Mocket._entries, {
            ('localhost', 80): [entry_1, entry_2],
            ('localhost', 8080): [entry_3],
        })

    def test_collect(self):
        request = 'GET /get/p/?b=2&a=1 HTTP/1.1\r\nAccept-Encoding: identity\r\nHost: testme.org\r\nConnection: close\r\nUser-Agent: Python-urllib/2.6\r\n\r\n'
        Mocket.collect(request)
        self.assertEqual(Mocket.last_request(), request)
        self.assertEqual(Mocket._requests, [request])

    def test_remove_last(self):
        Mocket._requests = [1, 2]
        Mocket.remove_last_request()
        self.assertEqual(Mocket._requests, [1])

    def test_remove_last_empty(self):
        Mocket.remove_last_request()
        self.assertEqual(Mocket._requests, [])

    def test_getentry(self):
        entry = MocketEntry(('localhost', 80), True)
        Mocket.register(entry)
        self.assertEqual(Mocket.get_entry('localhost', 80, True), entry)

    def test_getresponse(self):
        entry = MocketEntry(('localhost', 8080), ['Show me.\r\n'])
        self.assertEqual(entry.get_response(), encode_to_bytes('Show me.\r\n'))

    def test_empty_getresponse(self):
        entry = MocketEntry(('localhost', 8080), [])
        self.assertEqual(entry.get_response(), encode_to_bytes(''))
        
    def test_subsequent_recv_requests_have_correct_length(self):
        Mocket.register(
            MocketEntry(
                ('localhost', 80),
                [
                    b'Long payload',
                    b'Short'
                ]
            )
        )
        with Mocketizer():
            _so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _so.connect(('localhost', 80))
            _so.sendall(b'first\r\n')
            assert _so.recv(4096) == b'Long payload'
            _so.sendall(b'second\r\n')
            assert _so.recv(4096) == b'Short'
            _so.close()


class MocketizeTestCase(TestCase):
    def mocketize_setup(self):
        pass

    def mocketize_teardown(self):
        pass

    @mocketize
    def test_gethostname(self):
        self.assertEqual(socket.gethostname(), 'localhost')


@mocketize
def test_mocketize_outside_a_test_class():
    assert 2 == 2


@pytest.fixture
def fixture():
    return 2


@mocketize
def test_mocketize_with_fixture(fixture):
    assert 2 == fixture
