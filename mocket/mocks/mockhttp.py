import re
import time
from functools import cached_property
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlsplit

from h11 import SERVER, Connection, Data
from h11 import Request as H11Request

from mocket.compat import ENCODING, decode_from_bytes, do_the_magic, encode_to_bytes
from mocket.entry import MocketEntry
from mocket.mocket import Mocket

STATUS = {k: v[0] for k, v in BaseHTTPRequestHandler.responses.items()}
CRLF = "\r\n"
ASCII = "ascii"


class Request:
    _parser = None
    _event = None

    def __init__(self, data):
        self._parser = Connection(SERVER)
        self.add_data(data)

    def add_data(self, data):
        self._parser.receive_data(data)

    @property
    def event(self):
        if not self._event:
            self._event = self._parser.next_event()
        return self._event

    @cached_property
    def method(self):
        return self.event.method.decode(ASCII)

    @cached_property
    def path(self):
        return self.event.target.decode(ASCII)

    @cached_property
    def headers(self):
        return {k.decode(ASCII): v.decode(ASCII) for k, v in self.event.headers}

    @cached_property
    def querystring(self):
        parts = self.path.split("?", 1)
        return (
            parse_qs(unquote(parts[1]), keep_blank_values=True)
            if len(parts) == 2
            else {}
        )

    @cached_property
    def body(self):
        while True:
            event = self._parser.next_event()
            if isinstance(event, H11Request):
                self._event = event
            elif isinstance(event, Data):
                return event.data.decode(ENCODING)

    def __str__(self):
        return f"{self.method} - {self.path} - {self.headers}"


class Response:
    headers = None
    is_file_object = False

    def __init__(self, body="", status=200, headers=None):
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

    def get_protocol_data(self, str_format_fun_name: str = "capitalize") -> bytes:
        status_line = f"HTTP/1.1 {self.status} {STATUS[self.status]}"
        header_lines = CRLF.join(
            (
                f"{getattr(k, str_format_fun_name)()}: {v}"
                for k, v in self.headers.items()
            )
        )
        return f"{status_line}\r\n{header_lines}\r\n\r\n".encode(ENCODING)

    def set_base_headers(self):
        self.headers = {
            "Status": str(self.status),
            "Date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            "Server": "Python/Mocket",
            "Connection": "close",
            "Content-Length": str(len(self.body)),
        }
        if not self.is_file_object:
            self.headers["Content-Type"] = f"text/plain; charset={ENCODING}"
        else:
            self.headers["Content-Type"] = do_the_magic(self.body)

    def set_extra_headers(self, headers):
        r"""
        >>> r = Response(body="<html />")
        >>> len(r.headers.keys())
        6
        >>> r.set_extra_headers({"foo-bar": "Foobar"})
        >>> len(r.headers.keys())
        7
        >>> encode_to_bytes(r.headers.get("Foo-Bar")) == encode_to_bytes("Foobar")
        True
        """
        for k, v in headers.items():
            self.headers["-".join(token.capitalize() for token in k.split("-"))] = v


class Entry(MocketEntry):
    CONNECT = "CONNECT"
    DELETE = "DELETE"
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"
    TRACE = "TRACE"

    METHODS = (CONNECT, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, TRACE)

    request_cls = Request
    response_cls = Response

    def __init__(self, uri, method, responses, match_querystring=True):
        uri = urlsplit(uri)

        port = uri.port
        if not port:
            port = 443 if uri.scheme == "https" else 80

        super().__init__((uri.hostname, port), responses)
        self.schema = uri.scheme
        self.path = uri.path
        self.query = uri.query
        self.method = method.upper()
        self._sent_data = b""
        self._match_querystring = match_querystring

    def __repr__(self):
        return f"{self.__class__.__name__}(method={self.method!r}, schema={self.schema!r}, location={self.location!r}, path={self.path!r}, query={self.query!r})"

    def collect(self, data):
        consume_response = True

        decoded_data = decode_from_bytes(data)
        if not decoded_data.startswith(Entry.METHODS):
            Mocket.remove_last_request()
            self._sent_data += data
            consume_response = False
        else:
            self._sent_data = data

        super().collect(self._sent_data)

        return consume_response

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
            method, path, _ = self._parse_requestline(requestline)
        except ValueError:
            return self is getattr(Mocket, "_last_entry", None)

        uri = urlsplit(path)
        can_handle = uri.path == self.path and method == self.method
        if self._match_querystring:
            kw = dict(keep_blank_values=True)
            can_handle = can_handle and parse_qs(uri.query, **kw) == parse_qs(
                self.query, **kw
            )
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
        m = re.match(
            r"({})\s+(.*)\s+HTTP/(1.[0|1])".format("|".join(Entry.METHODS)), line, re.I
        )
        if m:
            return m.group(1).upper(), m.group(2), m.group(3)
        raise ValueError("Not a Request-Line")

    @classmethod
    def register(cls, method, uri, *responses, **config):
        if "body" in config or "status" in config:
            raise AttributeError("Did you mean `Entry.single_register(...)`?")

        default_config = dict(match_querystring=True, add_trailing_slash=True)
        default_config.update(config)
        config = default_config

        if config["add_trailing_slash"] and not urlsplit(uri).path:
            uri += "/"

        Mocket.register(
            cls(uri, method, responses, match_querystring=config["match_querystring"])
        )

    @classmethod
    def single_register(
        cls,
        method,
        uri,
        body="",
        status=200,
        headers=None,
        match_querystring=True,
        exception=None,
    ):
        response = (
            exception
            if exception
            else cls.response_cls(body=body, status=status, headers=headers)
        )

        cls.register(
            method,
            uri,
            response,
            match_querystring=match_querystring,
        )
