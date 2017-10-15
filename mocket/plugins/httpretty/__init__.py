from mocket import mocketize, Mocket
from mocket.mockhttp import Entry as MocketHttpEntry, Response as MocketHttpResponse, STATUS, CRLF
from mocket.compat import text_type, byte_type, encode_to_bytes


def httprettifier_headers(headers):
    return {k.lower().replace('_', '-'): v for k, v in headers.items()}


class Response(MocketHttpResponse):
    def get_protocol_data(self):
        status_line = 'HTTP/1.1 {status_code} {status}'.format(status_code=self.status, status=STATUS[self.status])
        if 'server' in self.headers and self.headers['server'] == 'Python/Mocket':
            self.headers['server'] = 'Python/HTTPretty'
        header_lines = CRLF.join(['{0}: {1}'.format(k.lower(), v) for k, v in self.headers.items()])
        return '{0}\r\n{1}\r\n\r\n'.format(status_line, header_lines).encode('utf-8')

    def set_base_headers(self):
        super(Response, self).set_base_headers()
        self.headers = httprettifier_headers(self.headers)
    original_set_base_headers = set_base_headers

    def set_extra_headers(self, headers):
        self.headers.update(headers)


class Entry(MocketHttpEntry):
    response_cls = Response


activate = mocketize
httprettified = mocketize
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
    body='HTTPretty :)',
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
            method, uri, body=body, status=status, headers=headers, match_querystring=match_querystring
        )


class MocketHTTPretty:

    Response = Response

    def __init__(self):
        pass

    def __getattr__(self, name):
        if name == 'last_request':
            last_request = getattr(Mocket, 'last_request')()
            last_request.body = encode_to_bytes(last_request.body)
            return last_request
        elif name == 'latest_requests':
            return getattr(Mocket, '_requests')
        else:
            return getattr(Entry, name)


HTTPretty = MocketHTTPretty()
HTTPretty.register_uri = register_uri


__all__ = (
    HTTPretty, activate, httprettified, enable, disable, reset, Response, GET, PUT, POST, DELETE, HEAD, PATCH,
    register_uri, text_type, byte_type
)
