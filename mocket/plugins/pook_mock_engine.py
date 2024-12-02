from __future__ import annotations

from typing import Any, Sequence

from mocket.core.mocket import Mocket
from mocket.http import MocketHttpEntry, MocketHttpMethod, MocketHttpResponse

try:
    from pook import Engine as PookEngine
    from pook import Mock as PookMock
    from pook import MockEngine as PookMockEngine
    from pook import Request as PookRequest
    from pook.interceptors.base import BaseInterceptor as PookBaseInterceptor
except ModuleNotFoundError:
    PookEngine = object
    PookMock = object
    PookMockEngine = object
    PookRequest = object
    PookBaseInterceptor = object


class MocketPookEntry(MocketHttpEntry):
    pook_request = None
    pook_engine = None

    def __init__(
        self,
        method: MocketHttpMethod,
        uri: str,
        responses: Sequence[MocketHttpResponse | Exception],
        pook_engine: PookEngine,
        pook_request: PookRequest,
        match_querystring: bool = True,
        add_trailing_slash: bool = True,
    ) -> None:
        super().__init__(
            method=method,
            uri=uri,
            responses=responses,
            match_querystring=match_querystring,
            add_trailing_slash=add_trailing_slash,
        )
        self._pook_engine = pook_engine
        self._pook_request = pook_request

    def can_handle(self, data: bytes) -> bool:
        can_handle = super().can_handle(data)

        if can_handle:
            self._pook_engine.match(self._pook_request)
        return can_handle


class MocketInterceptor(PookBaseInterceptor):  # type: ignore[misc]
    @staticmethod
    def activate() -> None:
        Mocket.disable()
        Mocket.enable()

    @staticmethod
    def disable() -> None:
        Mocket.disable()


class MocketEngine(PookMockEngine):  # type: ignore[misc]
    def __init__(self, engine: PookEngine) -> None:
        # Store plugins engine
        self.engine = engine
        # Store HTTP client interceptors
        self.interceptors: list[PookBaseInterceptor] = []
        # Self-register MocketInterceptor
        self.add_interceptor(MocketInterceptor)

        # mocking pook.mock()
        self.pook_mock_fun = self.engine.mock
        self.engine.mock = self.mocket_mock_fun

    def mocket_mock_fun(self, *args: Any, **kwargs: Any) -> PookMock:
        mock = self.pook_mock_fun(*args, **kwargs)

        request = mock._request
        method = request.method
        url = request.rawurl

        response = mock._response
        body = response._body
        status = response._status
        headers = response._headers

        entry = MocketPookEntry(
            method=method,
            uri=url,
            responses=[
                MocketHttpResponse(
                    status_code=status,
                    headers=headers,
                    body=body,
                )
            ],
            pook_engine=self.engine,
            pook_request=request,
        )
        Mocket.register(entry)

        return mock
