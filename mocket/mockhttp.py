# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import time
from io import BytesIO
import magic
from .compat import BaseHTTPRequestHandler, urlsplit, parse_qs, encode_utf8, decode_utf8
from .mocket import Mocket, MocketEntry
STATUS = dict([(k, v[0]) for k, v in BaseHTTPRequestHandler.responses.items()])
CRLF = '\r\n'


class Request(BaseHTTPRequestHandler):
    def __init__(self, data):
        _, self.body = decode_utf8(data).split('\r\n\r\n', 1)
        self.rfile = BytesIO(encode_utf8(data))
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.method = self.command


class Response(object):
    def __init__(self, body='', status=200, headers=None):
        headers = headers or {}
        is_file_object = False
        try:
            #  File Objects
            self.body = body.read()
            is_file_object = True
        except AttributeError:
            self.body = encode_utf8(body)
        self.status = status
        self.headers = {
            'Status': str(self.status),
            'Date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
            'Server': 'Python/Mocket',
            'Connection': 'close',
            'Content-Length': str(len(self.body)),
        }
        if not is_file_object:
            self.headers['Content-Type'] = 'text/plain; charset=utf-8'
        else:
            self.headers['Content-Type'] = decode_utf8(magic.from_buffer(self.body, mime=True))
        for k, v in headers.items():
            self.headers['-'.join([token.capitalize() for token in k.split('-')])] = v
        self.data = self.get_protocol_data() + self.body

    def get_protocol_data(self):
        status_line = 'HTTP/1.1 {status_code} {status}'.format(status_code=self.status, status=STATUS[self.status])
        header_lines = CRLF.join(['{0}: {1}'.format(k.capitalize(), v) for k, v in self.headers.items()])
        return '{0}\r\n{1}\r\n\r\n'.format(status_line, header_lines).encode('utf-8')


class Entry(MocketEntry):
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    DELETE = 'DELETE'
    HEAD = 'HEAD'
    PATCH = 'PATCH'
    METHODS = (GET, PUT, POST, DELETE, HEAD, PATCH)
    request_cls = Request
    response_cls = Response

    def __init__(self, uri, method, responses):
        uri = urlsplit(uri)
        super(Entry, self).__init__((uri.hostname, uri.port or 80), responses)
        self.schema = uri.scheme
        self.path = uri.path
        self.query = uri.query
        self.method = method.upper()
        self._sent_data = b''

    def collect(self, data):
        self._sent_data += data
        return super(Entry, self).collect(self._sent_data)

    def can_handle(self, data):
        try:
            requestline, _ = decode_utf8(data).split(CRLF, 1)
            method, path, version = self._parse_requestline(requestline)
        except ValueError:
            Mocket.remove_last_request()
            return True
        uri = urlsplit(path)
        return uri.path == self.path and parse_qs(uri.query) == parse_qs(self.query)

    @staticmethod
    def _parse_requestline(line):
        """
        http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5

        >>> Entry._parse_requestline('GET / HTTP/1.0') == ('GET', '/', '1.0')
        True
        >>> Entry._parse_requestline('post /testurl htTP/1.1') == ('POST', '/testurl', '1.1')
        True
        >>> Entry._parse_requestline('Im not a RequestLine')
        Traceback (most recent call last):
            ...
        ValueError: Not a Request-Line
        """
        methods = '|'.join(Entry.METHODS)
        m = re.match(r'(' + methods + ')\s+(.*)\s+HTTP/(1.[0|1])', line, re.I)
        if m:
            return m.group(1).upper(), m.group(2), m.group(3)
        else:
            raise ValueError('Not a Request-Line')

    @staticmethod
    def register(method, uri, *responses):
        Mocket.register(Entry(uri, method, responses))

    @staticmethod
    def single_register(method, uri, body='', status=200, headers=None):
        Entry.register(method, uri, Response(body=body, status=status, headers=headers))
