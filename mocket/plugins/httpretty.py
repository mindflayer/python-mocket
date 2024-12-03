from __future__ import annotations

from mocket.core.async_mocket import async_mocketize
from mocket.core.mocket import Mocket
from mocket.core.mocketizer import mocketize
from mocket.http import (
    MocketHttpEntry,
    MocketHttpMethod,
    MocketHttpRequest,
    MocketHttpResponse,
)


class MocketHttprettyResponse(MocketHttpResponse):
    server = "Python/HTTPretty"

    def __init__(
        self,
        body: str | bytes = "",
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status,
            headers=headers,
            body=body,
        )

    @property
    def status(self) -> int:
        return self.status_code

    @classmethod
    def _format_header_key(cls, key: str) -> str:
        return key.lower().replace("_", "-")


class MocketHttprettyEntry(MocketHttpEntry):
    response_cls = MocketHttprettyResponse  # type: ignore[assignment]


class MocketHTTPretty:
    Response = MocketHttprettyResponse

    CONNECT = MocketHttpMethod.CONNECT
    DELETE = MocketHttpMethod.DELETE
    GET = MocketHttpMethod.GET
    HEAD = MocketHttpMethod.HEAD
    OPTIONS = MocketHttpMethod.OPTIONS
    PATCH = MocketHttpMethod.PATCH
    POST = MocketHttpMethod.POST
    PUT = MocketHttpMethod.PUT
    TRACE = MocketHttpMethod.TRACE

    @property
    def latest_requests(self) -> list[MocketHttpRequest]:
        return Mocket.request_list()  # type: ignore[return-value]

    @property
    def last_request(self) -> MocketHttpRequest:
        return Mocket.last_request()  # type: ignore[return-value]

    def register_uri(
        self,
        method: MocketHttpMethod,
        uri: str,
        body: str | bytes = "HTTPretty :)",
        adding_headers: dict[str, str] | None = None,
        forcing_headers: dict[str, str] | None = None,
        status: int = 200,
        responses: list[MocketHttpResponse] | None = None,
        match_querystring: bool = False,
        priority: int = 0,
        **headers: str,
    ) -> None:
        if adding_headers is not None:
            headers.update(adding_headers)

        if responses is None:
            response = MocketHttprettyResponse(
                body=body,
                status=status,
                headers=headers,
            )
            responses = [response]

        if forcing_headers is not None:
            for r in responses:
                r.set_headers(forcing_headers)

        MocketHttpEntry.register_responses(
            method=method,
            uri=uri,
            responses=responses,
            match_querystring=match_querystring,
        )


HTTPretty = MocketHTTPretty()
httpretty = HTTPretty

Response = HTTPretty.Response

CONNECT = HTTPretty.CONNECT
DELETE = HTTPretty.DELETE
GET = HTTPretty.GET
HEAD = HTTPretty.HEAD
OPTIONS = HTTPretty.OPTIONS
PATCH = HTTPretty.PATCH
POST = HTTPretty.POST
PUT = HTTPretty.PUT
TRACE = HTTPretty.TRACE

activate = mocketize
httprettified = mocketize
async_httprettified = async_mocketize
register_uri = HTTPretty.register_uri

enable = Mocket.enable
disable = Mocket.disable
reset = Mocket.reset


__all__ = [
    "HTTPretty",
    "httpretty",
    "activate",
    "httprettified",
    "async_httprettified",
    "register_uri",
    "enable",
    "disable",
    "reset",
    "CONNECT",
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
    "TRACE",
    "Response",
]
