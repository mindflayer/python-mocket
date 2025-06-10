from typing import Any, Dict, Optional

from mocket import mocketize
from mocket.async_mocket import async_mocketize
from mocket.compat import ENCODING
from mocket.mocket import Mocket
from mocket.mockhttp import Entry as MocketHttpEntry
from mocket.mockhttp import Request as MocketHttpRequest
from mocket.mockhttp import Response as MocketHttpResponse


def httprettifier_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k.lower().replace("_", "-"): v for k, v in headers.items()}


class Request(MocketHttpRequest):
    @property
    def body(self) -> bytes:
        return super().body.encode(ENCODING)  # type: ignore[no-any-return]

    @property
    def headers(self) -> Dict[str, str]:
        return httprettifier_headers(super().headers)


class Response(MocketHttpResponse):
    headers: Dict[str, str]

    def get_protocol_data(self, str_format_fun_name: str = "lower") -> bytes:
        if "server" in self.headers and self.headers["server"] == "Python/Mocket":
            self.headers["server"] = "Python/HTTPretty"
        return super().get_protocol_data(str_format_fun_name=str_format_fun_name)  # type: ignore[no-any-return]

    def set_base_headers(self) -> None:
        super().set_base_headers()
        self.headers = httprettifier_headers(self.headers)

    original_set_base_headers = set_base_headers

    def set_extra_headers(self, headers: Dict[str, str]) -> None:
        self.headers.update(headers)


class Entry(MocketHttpEntry):
    request_cls = Request
    response_cls = Response


activate = mocketize
httprettified = mocketize
async_httprettified = async_mocketize

enable = Mocket.enable
disable = Mocket.disable
reset = Mocket.reset

GET = Entry.GET
PUT = Entry.PUT
POST = Entry.POST
DELETE = Entry.DELETE
HEAD = Entry.HEAD
PATCH = Entry.PATCH
OPTIONS = Entry.OPTIONS


def register_uri(
    method: str,
    uri: str,
    body: str = "HTTPretty :)",
    adding_headers: Optional[Dict[str, str]] = None,
    forcing_headers: Optional[Dict[str, str]] = None,
    status: int = 200,
    responses: Any = None,
    match_querystring: bool = False,
    priority: int = 0,
    **headers: str,
) -> None:
    headers = httprettifier_headers(headers)

    if adding_headers is not None:
        headers.update(httprettifier_headers(adding_headers))

    if forcing_headers is not None:

        def force_headers(self):
            self.headers = httprettifier_headers(forcing_headers)

        Response.set_base_headers = force_headers  # type: ignore[method-assign]
    else:
        Response.set_base_headers = Response.original_set_base_headers  # type: ignore[method-assign]

    if responses:
        Entry.register(
            method,
            uri,
            *responses,
            match_querystring=match_querystring,
        )
    else:
        Entry.single_register(
            method,
            uri,
            body=body,
            status=status,
            headers=headers,
            match_querystring=match_querystring,
        )


class MocketHTTPretty:
    Response = Response

    def __getattr__(self, name):
        if name == "last_request":
            return Mocket.last_request()
        if name == "latest_requests":
            return Mocket.request_list()
        return getattr(Entry, name)


HTTPretty = MocketHTTPretty()
HTTPretty.register_uri = register_uri  # type: ignore[attr-defined]
httpretty = HTTPretty

__all__ = (
    "HTTPretty",
    "httpretty",
    "activate",
    "async_httprettified",
    "httprettified",
    "enable",
    "disable",
    "reset",
    "Response",
    "GET",
    "PUT",
    "POST",
    "DELETE",
    "HEAD",
    "PATCH",
    "register_uri",
    "str",
    "bytes",
)
