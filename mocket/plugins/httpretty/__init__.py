from sys import version_info

from mocket import Mocket, mocketize
from mocket.compat import byte_type, text_type
from mocket.mockhttp import Entry as MocketHttpEntry
from mocket.mockhttp import Request as MocketHttpRequest
from mocket.mockhttp import Response as MocketHttpResponse


def httprettifier_headers(headers):
    return {k.lower().replace("_", "-"): v for k, v in headers.items()}


class Request(MocketHttpRequest):
    @property
    def body(self):
        if self._body is None:
            self._body = self.parser.recv_body()
        return self._body


class Response(MocketHttpResponse):
    def get_protocol_data(self, str_format_fun_name="lower"):
        if "server" in self.headers and self.headers["server"] == "Python/Mocket":
            self.headers["server"] = "Python/HTTPretty"
        return super(Response, self).get_protocol_data(
            str_format_fun_name=str_format_fun_name
        )

    def set_base_headers(self):
        super(Response, self).set_base_headers()
        self.headers = httprettifier_headers(self.headers)

    original_set_base_headers = set_base_headers

    def set_extra_headers(self, headers):
        self.headers.update(headers)


class Entry(MocketHttpEntry):
    request_cls = Request
    response_cls = Response


activate = mocketize
httprettified = mocketize

major, minor = version_info[:2]
if major == 3 and minor >= 5:
    from mocket.async_mocket import get_async_mocketize

    async_httprettified = get_async_mocketize()

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
    method,
    uri,
    body="HTTPretty :)",
    adding_headers=None,
    forcing_headers=None,
    status=200,
    responses=None,
    match_querystring=False,
    priority=0,
    **headers
):

    headers = httprettifier_headers(headers)

    if adding_headers is not None:
        headers.update(httprettifier_headers(adding_headers))

    if forcing_headers is not None:

        def force_headers(self):
            self.headers = httprettifier_headers(forcing_headers)

        Response.set_base_headers = force_headers
    else:
        Response.set_base_headers = Response.original_set_base_headers

    if responses:
        Entry.register(method, uri, *responses)
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

    def __init__(self):
        pass

    def __getattr__(self, name):
        if name == "last_request":
            last_request = getattr(Mocket, "last_request")()
            return last_request
        elif name == "latest_requests":
            return getattr(Mocket, "_requests")
        else:
            return getattr(Entry, name)


HTTPretty = MocketHTTPretty()
HTTPretty.register_uri = register_uri
httpretty = HTTPretty

__all__ = (
    "HTTPretty",
    "activate",
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
    "text_type",
    "byte_type",
)
