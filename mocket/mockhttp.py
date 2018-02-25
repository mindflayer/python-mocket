# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import time
from io import BytesIO

import magic

from .compat import (
    BaseHTTPRequestHandler,
    urlsplit,
    parse_qs,
    encode_to_bytes,
    decode_from_bytes,
    unquote_utf8,
)
from .mocket import Mocket, MocketEntry


STATUS = dict([(k, v[0]) for k, v in BaseHTTPRequestHandler.responses.items()])
CRLF = '\r\n'


class Request(BaseHTTPRequestHandler):
    def __init__(self, data):
        _, self.body = decode_from_bytes(data).split('\r\n\r\n', 1)
        self.rfile = BytesIO(encode_to_bytes(data))
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.method = self.command
        self.querystring = parse_qs(unquote_utf8(urlsplit(self.path).query), keep_blank_values=True)

    def add_data(self, data):
        self.body += data

    def __str__(self):
        return "{} - {} - {}".format(self.method, self.path, self.headers)


class Response(object):
    headers = None
    is_file_object = False

    def __init__(self, body='', status=200, headers=None):
        headers = headers or {}
        try:
            #  File Objects
            self.body = body.read()
            self.is_file_object = True
        except AttributeError:
            self.body = encode_to_bytes(body)
        self.status = status

        self.set_base_headers()

        if headers is not None:
            self.set_extra_headers(headers)

        self.data = self.get_protocol_data() + self.body

    def get_protocol_data(self):
        status_line = 'HTTP/1.1 {status_code} {status}'.format(status_code=self.status, status=STATUS[self.status])
        header_lines = CRLF.join(['{0}: {1}'.format(k.capitalize(), v) for k, v in self.headers.items()])
        return '{0}\r\n{1}\r\n\r\n'.format(status_line, header_lines).encode('utf-8')

    def set_base_headers(self):
        self.headers = {
            'Status': str(self.status),
            'Date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
            'Server': 'Python/Mocket',
            'Connection': 'close',
            'Content-Length': str(len(self.body)),
        }
        if not self.is_file_object:
            self.headers['Content-Type'] = 'text/plain; charset=utf-8'
        else:
            self.headers['Content-Type'] = decode_from_bytes(magic.from_buffer(self.body, mime=True))

    def set_extra_headers(self, headers):
        for k, v in headers.items():
            self.headers['-'.join([token.capitalize() for token in k.split('-')])] = v


class Entry(MocketEntry):
    CONNECT = 'CONNECT'
    DELETE = 'DELETE'
    GET = 'GET'
    HEAD = 'HEAD'
    OPTIONS = 'OPTIONS'
    PATCH = 'PATCH'
    POST = 'POST'
    PUT = 'PUT'
    TRACE = 'TRACE'

    METHODS = (CONNECT, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, TRACE)

    request_cls = Request
    response_cls = Response

    def __init__(self, uri, method, responses, match_querystring=True):
        uri = urlsplit(uri)

        if not uri.port:
            if uri.scheme == 'https':
                port = 443
            else:
                port = 80

        super(Entry, self).__init__((uri.hostname, uri.port or port), responses)
        self.schema = uri.scheme
        self.path = uri.path
        self.query = uri.query
        self.method = method.upper()
        self._sent_data = b''
        self._match_querystring = match_querystring

    def collect(self, data):
        self._sent_data += data
        super(Entry, self).collect(self._sent_data)

    def can_handle(self, data):
        r"""
        >>> e = Entry('http://www.github.com/?bar=foo&foobar', Entry.GET, (Response(b'<html/>'),))
        >>> e.can_handle(b'GET /?bar=foo HTTP/1.1\r\nHost: github.com\r\nAccept-Encoding: gzip, deflate\r\nConnection: keep-alive\r\nUser-Agent: python-requests/2.7.0 CPython/3.4.3 Linux/3.19.0-16-generic\r\nAccept: */*\r\n\r\n')
        False
        >>> e = Entry('http://www.github.com/?bar=foo&foobar', Entry.GET, (Response(b'<html/>'),))
        >>> e.can_handle(b'GET /?bar=foo&foobar HTTP/1.1\r\nHost: github.com\r\nAccept-Encoding: gzip, deflate\r\nConnection: keep-alive\r\nUser-Agent: python-requests/2.7.0 CPython/3.4.3 Linux/3.19.0-16-generic\r\nAccept: */*\r\n\r\n')
        True
        """
        try:
            requestline, _ = decode_from_bytes(data).split(CRLF, 1)
            method, path, version = self._parse_requestline(requestline)
        except ValueError:
            try:
                same_entry = self == Mocket._last_entry
                if same_entry:
                    Mocket.remove_last_request()
                return same_entry
            except AttributeError:
                return False
        uri = urlsplit(path)
        can_handle = uri.path == self.path and method == self.method
        if self._match_querystring:
            kw = dict(keep_blank_values=True)
            can_handle = can_handle and parse_qs(uri.query, **kw) == parse_qs(self.query, **kw)
        if can_handle:
            Mocket._last_entry = self
        return can_handle

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

    @classmethod
    def register(cls, method, uri, *responses, **config):

        default_config = dict(match_querystring=True, add_trailing_slash=True)
        default_config.update(config)
        config = default_config

        if config['add_trailing_slash'] and not urlsplit(uri).path:
            uri += '/'

        Mocket.register(cls(uri, method, responses, match_querystring=config['match_querystring']))

    @classmethod
    def single_register(cls, method, uri, body='', status=200, headers=None, match_querystring=True):
        cls.register(
            method, uri, cls.response_cls(
                body=body, status=status, headers=headers
            ), match_querystring=match_querystring
        )
