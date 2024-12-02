from __future__ import annotations

from typing import Sequence

from typing_extensions import Self

from mocket.core.entry import MocketBaseEntry, MocketBaseRequest, MocketBaseResponse
from mocket.core.mocket import Mocket
from mocket.core.types import Address


class MocketBytesRequest(MocketBaseRequest):
    def __init__(self) -> None:
        self._data = b""

    @property
    def data(self) -> bytes:
        return self._data

    @classmethod
    def from_data(cls: type[Self], data: bytes) -> Self:
        request = cls()
        request._data = data
        return request


class MocketBytesResponse(MocketBaseResponse):
    def __init__(self, data: bytes | str | bool) -> None:
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, bool):
            data = bytes(data)
        self._data = data

    @property
    def data(self) -> bytes:
        return self._data


class MocketBytesEntry(MocketBaseEntry):
    request_cls = MocketBytesRequest
    response_cls = MocketBytesResponse

    def __init__(
        self,
        address: Address,
        responses: Sequence[MocketBytesResponse | Exception],
    ) -> None:
        if not len(responses):
            responses = [MocketBytesResponse(data=b"")]

        super().__init__(
            address=address,
            responses=responses,
        )

    @classmethod
    def register_response(
        cls,
        address: Address,
        response: MocketBytesResponse | Exception,
    ) -> None:
        entry = cls(
            address=address,
            responses=[response],
        )
        Mocket.register(entry)

    @classmethod
    def register_responses(
        cls,
        address: Address,
        responses: Sequence[MocketBytesResponse | Exception],
    ) -> None:
        entry = cls(
            address=address,
            responses=responses,
        )
        Mocket.register(entry)
