from .mocket import mocketize, Mocket
from .mockhttp import Entry, Response

activate = mocketize
enable = Mocket.enable
disable = Mocket.disable
reset = Mocket.reset
last_request = Mocket.last_request

GET = Entry.GET
PUT = Entry.PUT
POST = Entry.POST
DELETE = Entry.DELETE
HEAD = Entry.HEAD
PATCH = Entry.PATCH


def register_uri(
    method,
    uri,
    body='HTTPretty :)',
    adding_headers=None,
    forcing_headers=None,
    status=200,
    responses=None,
    match_querystring=False,
    priority=0,
    **headers
):

    if adding_headers is not None:
        headers.update(adding_headers)

    if responses:
        Entry.register(method, uri, *responses)
    else:
        Entry.single_register(method, uri, body=body, status=status, headers=headers)


__all__ = (activate, enable, disable, reset, last_request, Response, GET, PUT, POST, DELETE, HEAD, PATCH, register_uri)
