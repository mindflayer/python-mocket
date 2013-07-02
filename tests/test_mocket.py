import socket
from unittest import TestCase
from mocket.mocket import Mocket, mocketize


class TestEntry(object):
    def __init__(self, hostname, port):
        self.location = (hostname, port)

    def can_handle(self, data):
        return data


class MocketTestCase(TestCase):
    def setUp(self):
        Mocket._entries = {}
        Mocket._requests = []

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
        self.assertEqual(socket.gethostbyname('localhost'), 'localhost')
        Mocket.disable()
        self.assertEqual(socket.gethostbyname('localhost'), host)

    def test_register(self):
        entry_1 = TestEntry('localhost', 80)
        entry_2 = TestEntry('localhost', 80)
        entry_3 = TestEntry('localhost', 8080)
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
        entry = TestEntry('localhost', 80)
        Mocket.register(entry)
        self.assertEqual(Mocket.get_entry('localhost', 80, True), entry)


class MocketizeTestCase(TestCase):
    def mocketize_setup(self):
        pass

    def mocketize_teardown(self):
        pass

    @mocketize
    def test_gethostname(self):
        self.assertEqual(socket.gethostname(), 'localhost')
