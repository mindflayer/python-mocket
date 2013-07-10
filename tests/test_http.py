# coding=utf-8
from __future__ import unicode_literals
import time
import mock
from . import urlopen, HTTPError
import pytest
import requests
from unittest import TestCase
from mocket.mockhttp import Entry, Response
from mocket.mocket import Mocket, mocketize


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
class TrueHttpEntryTestCase(TestCase):
    @mocketize
    def test_truesendall(self):
        resp = urlopen('http://httpbin.org/ip')
        self.assertEqual(resp.code, 200)
        resp = requests.get('http://httpbin.org/ip')
        self.assertEqual(resp.status_code, 200)

    @mocketize
    def test_wrongpath_truesendall(self):
        Entry.register(Entry.GET, 'http://httpbin.org/user.agent', Response())
        response = urlopen('http://httpbin.org/ip')
        self.assertEqual(response.code, 200)


class HttpEntryTestCase(TestCase):
    def test_register(self):
        with mock.patch('time.gmtime') as tt:
            tt.return_value = time.struct_time((2013, 4, 30, 10, 39, 21, 1, 120, 0))
            Entry.register(
                Entry.GET,
                'http://testme.org/get?a=1&b=2#test',
                Response('{"a": "€"}', headers={'content-type': 'application/json'})
            )
        entries = Mocket._entries[('testme.org', 80)]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.method, 'GET')
        self.assertEqual(entry.schema, 'http')
        self.assertEqual(entry.path, '/get')
        self.assertEqual(entry.query, 'a=1&b=2')
        self.assertEqual(len(entry.responses), 1)
        response = entry.responses[0]
        self.assertEqual(response.body, b'{"a": "\xe2\x82\xac"}')
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, {
            'Status': '200',
            'Date': 'Tue, 30 Apr 2013 10:39:21 GMT',
            'Connection': 'close',
            'Server': 'Python/Mocket',
            'Content-Length': '12',
            'Content-Type': 'application/json',
        })

    @mocketize
    def test_sendall(self):
        with mock.patch('time.gmtime') as tt:
            tt.return_value = time.struct_time((2013, 4, 30, 10, 39, 21, 1, 120, 0))
            Entry.single_register(Entry.GET, 'http://testme.org/get/p/?a=1&b=2', body='test_body')
        resp = urlopen('http://testme.org/get/p/?b=2&a=1', timeout=10)
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.read(), b'test_body')
        self.assertEqualHeaders(dict(resp.headers), {
            'Status': '200',
            'Content-length': '9',
            'Server': 'Python/Mocket',
            'Connection': 'close',
            'Date': 'Tue, 30 Apr 2013 10:39:21 GMT',
            'Content-type': 'text/plain; charset=utf-8'
        })
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_sendall_json(self):
        with mock.patch('time.gmtime') as tt:
            tt.return_value = time.struct_time((2013, 4, 30, 10, 39, 21, 1, 120, 0))
            Entry.single_register(
                Entry.GET,
                'http://testme.org/get?a=1&b=2#test',
                body='{"a": "€"}',
                headers={'content-type': 'application/json'}
            )

        response = urlopen('http://testme.org/get?b=2&a=1#test', timeout=10)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.read(), b'{"a": "\xe2\x82\xac"}')
        self.assertEqualHeaders(dict(response.headers), {
            'status': '200',
            'content-length': '12',
            'server': 'Python/Mocket',
            'connection': 'close',
            'date': 'Tue, 30 Apr 2013 10:39:21 GMT',
            'content-type': 'application/json',
        })
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_sendall_double(self):
        Entry.register(Entry.GET, 'http://testme.org/', Response(status=404), Response())
        self.assertRaises(HTTPError, urlopen, 'http://testme.org/')
        response = urlopen('http://testme.org/')
        self.assertEqual(response.code, 200)
        response = urlopen('http://testme.org/')
        self.assertEqual(response.code, 200)
        self.assertEqual(len(Mocket._requests), 3)

    @mocketize
    def test_multipart(self):
        url = 'http://httpbin.org/post'
        data = '--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="content"\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 68\r\n\r\nAction: comment\nText: Comment with attach\nAttachment: x1.txt, x2.txt\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_2"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_1"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz--\r\n'
        headers = {
            'Content-Length': '495',
            'Content-Type': 'multipart/form-data; boundary=xXXxXXyYYzzz',
            'Accept': 'text/plain',
            'User-Agent': 'Mocket',
            'Accept-encoding': 'identity',
        }
        Entry.register(Entry.POST, url)
        response = requests.post(url, data=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        last_request = Mocket.last_request()
        self.assertEqual(last_request.method, 'POST')
        self.assertEqual(last_request.path, '/post')
        self.assertEqual(last_request.body, data)
        sent_headers = dict(last_request.headers)
        self.assertEqualHeaders(sent_headers, {'accept': 'text/plain',
'accept-encoding': 'identity',
'content-length': '495',
'content-type': 'multipart/form-data; boundary=xXXxXXyYYzzz',
'host': 'httpbin.org',
'user-agent': 'Mocket'})

    def assertEqualHeaders(self, first, second, msg=None):
        first = dict([(k.lower(), v) for k, v in first.items()])
        second = dict([(k.lower(), v) for k, v in second.items()])
        self.assertEqual(first, second, msg)
