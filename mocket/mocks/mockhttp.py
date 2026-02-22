"""HTTP mocking implementation for Mocket."""

from __future__ import annotations

import re
import time
from functools import cached_property
from http.server import BaseHTTPRequestHandler
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from h11 import SERVER, Connection, Data
from h11 import Request as H11Request

from mocket.compat import ENCODING, decode_from_bytes, do_the_magic, encode_to_bytes
from mocket.entry import MocketEntry
from mocket.mocket import Mocket

STATUS: dict = {k: v[0] for k, v in BaseHTTPRequestHandler.responses.items()}
CRLF: str = "\r\n"
ASCII: str = "ascii"


class Request:
    """HTTP request parser using h11."""

    _parser: Connection | None = None
    _event: Any | None = None

    def __init__(self, data: bytes) -> None:
        """Initialize the request parser.

        Args:
            data: Raw HTTP request data
        """
        self._parser = Connection(SERVER)
        self.add_data(data)

    def add_data(self, data: bytes) -> None:
        """Add more data to the request.

        Args:
            data: Additional raw request data
        """
        self._parser.receive_data(data)

    @property
    def event(self) -> Any:
        """Get the parsed request event.

        Returns:
            The h11 request event
        """
        if not self._event:
            self._event = self._parser.next_event()
        return self._event

    @cached_property
    def method(self) -> str:
        """Get the HTTP method.

        Returns:
            HTTP method (GET, POST, etc.)
        """
        return self.event.method.decode(ASCII)

    @cached_property
    def path(self) -> str:
        """Get the request path.

        Returns:
            Request path with query string
        """
        return self.event.target.decode(ASCII)

    @cached_property
    def headers(self) -> dict:
        """Get the request headers.

        Returns:
            Dictionary of header names to values
        """
        return {k.decode(ASCII): v.decode(ASCII) for k, v in self.event.headers}

    @cached_property
    def querystring(self) -> dict:
        """Get the parsed query string.

        Returns:
            Dictionary of query parameter names to lists of values
        """
        parts = self.path.split("?", 1)
        return (
            parse_qs(unquote(parts[1]), keep_blank_values=True)
            if len(parts) == 2
            else {}
        )

    @cached_property
    def body(self) -> str:
        """Get the request body.

        Returns:
            Decoded request body string
        """
        while True:
            event = self._parser.next_event()
            if isinstance(event, H11Request):
                self._event = event
            elif isinstance(event, Data):
                return event.data.decode(ENCODING)

    def __str__(self) -> str:
        """Get string representation of request.

        Returns:
            Formatted request string
        """
        return f"{self.method} - {self.path} - {self.headers}"


class Response:
    """HTTP response builder."""

    headers: dict | None = None
    is_file_object: bool = False

    def __init__(
        self, body: Any = "", status: int = 200, headers: dict | None = None
    ) -> None:
        """Initialize an HTTP response.

        Args:
            body: Response body (string, bytes, or file-like object)
            status: HTTP status code
            headers: Dictionary of response headers
        """
        headers = headers or {}
        try:
            #  File Objects
            self.body = body.read()
            self.is_file_object = True
        except AttributeError:
            self.body = encode_to_bytes(body)
        self.status = status

        self.set_base_headers()
        self.set_extra_headers(headers)

        self.data = self.get_protocol_data() + self.body

    def get_protocol_data(self, str_format_fun_name: str = "capitalize") -> bytes:
        """Get the HTTP protocol headers and status line.

        Args:
            str_format_fun_name: Name of string formatting method to use

        Returns:
            Bytes of protocol headers (status line and headers)
        """
        status_line = f"HTTP/1.1 {self.status} {STATUS[self.status]}"
        header_lines = CRLF.join(
            (
                f"{getattr(k, str_format_fun_name)()}: {v}"
                for k, v in self.headers.items()
            )
        )
        return f"{status_line}\r\n{header_lines}\r\n\r\n".encode(ENCODING)

    def set_base_headers(self) -> None:
        """Set the base response headers."""
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

    def set_extra_headers(self, headers: dict) -> None:
        r"""Add extra headers to the response.

        Args:
            headers: Dictionary of additional headers

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
    """HTTP entry for matching and responding to HTTP requests."""

    CONNECT = "CONNECT"
    DELETE = "DELETE"
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"
    TRACE = "TRACE"

    METHODS: tuple = (CONNECT, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, TRACE)

    request_cls: type = Request
    response_cls: type = Response

    default_config: dict = {"match_querystring": True, "can_handle_fun": None}
    _can_handle_fun: Callable | None = None

    def __init__(
        self,
        uri: str,
        method: str,
        responses: Any,
        match_querystring: bool = True,
        can_handle_fun: Callable | None = None,
    ) -> None:
        """Initialize an HTTP entry.

        Args:
            uri: URI to match (http://host:port/path?query)
            method: HTTP method (GET, POST, etc.)
            responses: Response(s) to return
            match_querystring: Whether to match query strings
            can_handle_fun: Custom matching function
        """
        self._can_handle_fun = can_handle_fun if can_handle_fun else self._can_handle

        uri = urlsplit(uri)

        port = uri.port
        if not port:
            port = 443 if uri.scheme == "https" else 80

        super().__init__((uri.hostname, port), responses)
        self.schema = uri.scheme
        self.path = uri.path or "/"
        self.query = uri.query
        self.method = method.upper()
        self._sent_data = b""
        self._match_querystring = match_querystring

    def __repr__(self) -> str:
        """Get string representation of the entry.

        Returns:
            String representation
        """
        return f"{self.__class__.__name__}(method={self.method!r}, schema={self.schema!r}, location={self.location!r}, path={self.path!r}, query={self.query!r})"

    def collect(self, data: bytes) -> bool:
        """Collect the request data.

        Args:
            data: Request data

        Returns:
            Whether to consume the response
        """
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

    def _can_handle(self, path: str, qs_dict: dict) -> bool:
        """Default can_handle function checking path and query string.

        Args:
            path: Request path
            qs_dict: Parsed query string parameters

        Returns:
            True if this entry can handle the request
        """
        can_handle = path == self.path
        if self._match_querystring:
            can_handle = can_handle and qs_dict == parse_qs(
                self.query, keep_blank_values=True
            )
        return can_handle

    def can_handle(self, data: bytes) -> bool:
        r"""Check if this entry can handle the given request data.

        Args:
            data: Request data

        Returns:
            True if this entry can handle the request

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

        _request = urlsplit(path)

        can_handle = method == self.method and self._can_handle_fun(
            _request.path, parse_qs(_request.query, keep_blank_values=True)
        )

        if can_handle:
            Mocket._last_entry = self
        return can_handle

    @staticmethod
    def _parse_requestline(line: str) -> tuple:
        """Parse an HTTP request line.

        http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5

        Args:
            line: HTTP request line string

        Returns:
            Tuple of (method, path, version)

        Raises:
            ValueError: If line is not a valid request line

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
    def register(cls, method: str, uri: str, *responses: Any, **config: Any) -> None:
        """Register an HTTP entry for multiple responses.

        Args:
            method: HTTP method (GET, POST, etc.)
            uri: URI to match
            *responses: Response(s) to cycle through
            **config: Configuration options (match_querystring, can_handle_fun)

        Raises:
            AttributeError: If using body/status params (use single_register instead)
            KeyError: If invalid config keys provided
        """
        if "body" in config or "status" in config:
            raise AttributeError("Did you mean `Entry.single_register(...)`?")

        if config.keys() - cls.default_config.keys():
            raise KeyError(
                f"Invalid config keys: {config.keys() - cls.default_config.keys()}"
            )

        _config = cls.default_config.copy()
        _config.update({k: v for k, v in config.items() if k in _config})

        Mocket.register(cls(uri, method, responses, **_config))

    @classmethod
    def single_register(
        cls,
        method: str,
        uri: str,
        body: Any = "",
        status: int = 200,
        headers: dict | None = None,
        exception: Exception | None = None,
        match_querystring: bool = True,
        can_handle_fun: Callable | None = None,
        **config: Any,
    ) -> None:
        """Register a single HTTP response for a URI and method.

        This is a convenience method that creates a single Response object
        instead of requiring a list.

        Args:
            method: HTTP method (GET, POST, etc.)
            uri: URI to match
            body: Response body content
            status: HTTP status code
            headers: Dictionary of response headers
            exception: Exception to raise instead of returning response
            match_querystring: Whether to match query strings
            can_handle_fun: Custom matching function
            **config: Additional configuration options
        """
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
            can_handle_fun=can_handle_fun,
            **config,
        )
