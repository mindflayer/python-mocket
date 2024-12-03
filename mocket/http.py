from __future__ import annotations

import contextlib
import time
from enum import Enum
from http.server import BaseHTTPRequestHandler
from io import BufferedReader
from typing import ClassVar, Sequence
from urllib.parse import parse_qs, unquote, urlsplit

import h11
from typing_extensions import Self

from mocket.core.compat import ENCODING, do_the_magic
from mocket.core.entry import MocketBaseEntry, MocketBaseRequest, MocketBaseResponse
from mocket.core.mocket import Mocket

STATUS = {k: v[0] for k, v in BaseHTTPRequestHandler.responses.items()}
CRLF = "\r\n"
ASCII = "ascii"


class MocketHttpMethod(str, Enum):
    CONNECT = "CONNECT"
    DELETE = "DELETE"
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"
    TRACE = "TRACE"


class MocketHttpRequest(MocketBaseRequest):
    def __init__(self) -> None:
        super().__init__()

        self._parser = h11.Connection(h11.SERVER)

        self._method: MocketHttpMethod | None = None
        self._path: str | None = None
        self._querystring: dict[str, list[str]] | None = None
        self._headers: dict[str, str] | None = None
        self._body: bytes | None = None

        self._has_start_line: bool = False
        self._has_body: bool = False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"method='{self.method.name if self.method else None}', "
            f"path='{self.path}', "
            f"headers={self.headers}"
            ")"
        )

    @property
    def data(self) -> bytes:
        return bytes(self._parser._receive_buffer)

    @property
    def has_start_line(self) -> bool:
        return self._has_start_line

    @property
    def has_body(self) -> bool:
        return self._has_body

    @property
    def method(self) -> MocketHttpMethod | None:
        return self._method

    @property
    def path(self) -> str | None:
        return self._path

    @property
    def querystring(self) -> dict[str, list[str]] | None:
        return self._querystring

    @property
    def headers(self) -> dict[str, str] | None:
        return self._headers

    @property
    def body(self) -> bytes | None:
        return self._body

    def _add_data(self, data: bytes) -> None:
        self._parser.receive_data(data)
        while True:
            event = self._parser.next_event()
            if isinstance(event, h11.Request):
                self._set_h11_request(event)
            elif isinstance(event, h11.Data):
                self._set_h11_data(event)
            else:
                return

    def _set_h11_request(self, request: h11.Request) -> None:
        self._has_start_line = True
        self._method = MocketHttpMethod(request.method.decode(ASCII))
        self._path = request.target.decode(ASCII)
        self._querystring = self._parse_querystring(self._path)
        self._headers = {k.decode(ASCII): v.decode(ASCII) for k, v in request.headers}

    def _set_h11_data(self, data: h11.Data) -> None:
        self._has_body = True
        self._body = data.data

    @staticmethod
    def _parse_querystring(path: str) -> dict[str, list[str]]:
        parts = path.split("?", 1)
        return (
            parse_qs(unquote(parts[1]), keep_blank_values=True)
            if len(parts) == 2
            else {}
        )

    @classmethod
    def from_data(cls: type[Self], data: bytes) -> Self:
        request = cls()
        request._add_data(data)
        return request


class MocketHttpResponse(MocketBaseResponse):
    server: ClassVar[str] = "Python/Mocket"
    protocol: ClassVar[str] = "HTTP/1.1"

    def __init__(
        self,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        body: str | bytes | BufferedReader = b"",
    ):
        body_from_file = False
        if isinstance(body, str):
            body = body.encode()
        elif isinstance(body, BufferedReader):
            #  File Objects
            body = body.read()
            body_from_file = True

        self._status_code = status_code
        self._body = body
        self._headers: dict[str, str] = {}

        base_headers = self._get_base_headers(
            status_code=status_code,
            body=body,
            body_from_file=body_from_file,
        )

        self.set_headers(base_headers)
        self.add_headers(headers or {})

        super().__init__()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"headers={self.headers}, "
            f"body={self.body!r}"
            ")"
        )

    @property
    def data(self) -> bytes:
        return self._get_http_message(
            status_code=self._status_code,
            headers=self._headers,
            body=self._body,
        )

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> dict[str, str]:
        return self._headers

    @property
    def body(self) -> bytes:
        return self._body

    def set_headers(self, headers: dict[str, str]) -> None:
        self._headers = {}
        self.add_headers(headers)

    def add_headers(self, headers: dict[str, str]) -> None:
        for k, v in headers.items():
            formatted_key = self._format_header_key(k)
            self._headers[formatted_key] = v

    def set_extra_headers(self, headers: dict[str, str]) -> None:
        r"""
        >>> from mocket.core.utils import encode_to_bytes
        >>> r = MocketHttpResponse(body="<html />")
        >>> len(r.headers.keys())
        6
        >>> r.set_extra_headers({"foo-bar": "Foobar"})
        >>> len(r.headers.keys())
        7
        >>> encode_to_bytes(r.headers.get("Foo-Bar")) == encode_to_bytes("Foobar")
        True
        """
        self.add_headers(headers)

    @classmethod
    def _get_base_headers(
        cls,
        status_code: int,
        body: bytes,
        body_from_file: bool,
    ) -> dict[str, str]:
        if body_from_file:
            content_type = do_the_magic(body)
        else:
            content_type = f"text/plain; charset={ENCODING}"

        return {
            "Status": str(status_code),
            "Date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            "Server": cls.server,
            "Connection": "close",
            "Content-Length": str(len(body)),
            "Content-Type": content_type,
        }

    @classmethod
    def _format_header_key(cls, key: str) -> str:
        return "-".join(token.capitalize() for token in key.split("-"))

    @classmethod
    def _get_http_message(
        cls,
        status_code: int,
        headers: dict[str, str],
        body: bytes,
    ) -> bytes:
        protocol = cls.protocol
        status_text = STATUS[status_code]
        status_line = f"{protocol} {status_code} {status_text}"
        header_lines = [f"{k}: {v}" for k, v in headers.items()]
        head_lines = [status_line] + header_lines + [CRLF]
        head = CRLF.join(head_lines).encode(ENCODING)
        return head + body


class MocketHttpEntry(MocketBaseEntry):
    request_cls = MocketHttpRequest
    response_cls = MocketHttpResponse

    def __init__(
        self,
        method: MocketHttpMethod,
        uri: str,
        responses: Sequence[MocketHttpResponse | Exception],
        match_querystring: bool = True,
        add_trailing_slash: bool = True,
    ) -> None:
        uri_split = urlsplit(uri)

        host = uri_split.hostname or ""
        port = uri_split.port or (443 if uri_split.scheme == "https" else 80)

        responses = responses or [self.response_cls()]

        self._method = method
        self._scheme = uri_split.scheme
        self._path = uri_split.path or ("/" if add_trailing_slash else "")
        # TODO should this be query-string and be parsed as in request?
        self._query = uri_split.query
        self._match_querystring = match_querystring
        self._sent_data = b""

        super().__init__(address=(host, port), responses=responses)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"address={self.address}, "
            f"method='{self.method}', "
            f"scheme='{self.scheme}', "
            f"path='{self.path}', "
            f"query='{self.query}'"
            ")"
        )

    @property
    def method(self) -> MocketHttpMethod:
        return self._method

    @property
    def scheme(self) -> str:
        return self._scheme

    @property
    def path(self) -> str:
        return self._path

    @property
    def query(self) -> str:
        return self._query

    def can_handle(self, data: bytes) -> bool:
        request = None
        with contextlib.suppress(h11.RemoteProtocolError):
            # add a CRLF so that this _could_ be considered a complete http-head
            request = self.request_cls.from_data(data + CRLF.encode())

        if request is None or not request.has_start_line:
            return self is getattr(Mocket, "_last_entry", None)

        uri = urlsplit(request.path)
        path_match = uri.path == self._path
        method_match = request.method == self._method
        query_match = True

        if self._match_querystring:
            self_querystring = parse_qs(self._query, keep_blank_values=True)
            query_match = request.querystring == self_querystring

        can_handle = path_match and method_match and query_match
        if can_handle:
            Mocket._last_entry = self
        return can_handle

    # TODO dunno if i like this method here
    def collect(self, data: bytes) -> bool:
        consume_response = True

        methods = tuple([n.value.encode() for n in MocketHttpMethod])
        if data.startswith(methods):
            self._sent_data = data
        else:
            Mocket.remove_last_request()
            self._sent_data += data
            consume_response = False

        request = self.request_cls.from_data(self._sent_data)
        Mocket.collect(request)

        return consume_response

    @classmethod
    def register_response(
        cls,
        method: MocketHttpMethod,
        uri: str,
        body: str | bytes | BufferedReader = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        match_querystring: bool = True,
        exception: Exception | None = None,
    ) -> None:
        response: MocketHttpResponse | Exception
        if exception is not None:
            response = exception
        else:
            response = MocketHttpResponse(
                body=body,
                status_code=status_code,
                headers=headers,
            )

        cls.register_responses(
            method=method,
            uri=uri,
            responses=[response],
            match_querystring=match_querystring,
        )

    @classmethod
    def register_responses(
        cls,
        method: MocketHttpMethod,
        uri: str,
        responses: Sequence[MocketHttpResponse | Exception],
        match_querystring: bool = True,
        add_trailing_slash: bool = True,
    ) -> None:
        entry = cls(
            method=method,
            uri=uri,
            responses=responses,
            match_querystring=match_querystring,
            add_trailing_slash=add_trailing_slash,
        )
        Mocket.register(entry)
