from pook.engine import MockEngine
from pook.interceptors.base import BaseInterceptor

from mocket.mocket import Mocket
from mocket.mockhttp import Entry, Response


class MocketPookEntry(Entry):
    pook_request = None
    pook_engine = None

    def can_handle(self, data):
        can_handle = super(MocketPookEntry, self).can_handle(data)

        if can_handle:
            self.pook_engine.match(self.pook_request)
        return can_handle

    @classmethod
    def single_register(cls, method, uri, body='', status=200, headers=None, match_querystring=True):
        entry = cls(
            uri, method, Response(
                body=body, status=status, headers=headers
            ), match_querystring=match_querystring
        )
        Mocket.register(entry)
        return entry


class MocketInterceptor(BaseInterceptor):
    def activate(self):
        Mocket.disable()
        Mocket.enable()

    def disable(self):
        Mocket.disable()


class MocketEngine(MockEngine):

    def __init__(self, engine):
        def mocket_mock_fun(*args, **kwargs):
            mock = self.pook_mock_fun(*args, **kwargs)

            request = mock._request
            method = request.method
            url = request.rawurl

            response = mock._response
            body = response._body
            status = response._status
            headers = response._headers

            entry = MocketPookEntry.single_register(method, url, body, status, headers)
            entry.pook_engine = self.engine
            entry.pook_request = request

            return mock

        # Store plugins engine
        self.engine = engine
        # Store HTTP client interceptors
        self.interceptors = []
        # Self-register MocketInterceptor
        self.add_interceptor(MocketInterceptor)

        # mocking pook.mock()
        self.pook_mock_fun = self.engine.mock
        self.engine.mock = mocket_mock_fun
