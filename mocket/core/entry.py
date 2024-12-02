from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Sequence

from typing_extensions import Self

from mocket.core.mocket import Mocket
from mocket.core.types import Address


class MocketBaseRequest(ABC):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(data='{self.data!r}')"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, MocketBaseRequest):
            return self.data == other.data

        if isinstance(other, bytes):
            return self.data == other

        return False

    @property
    @abstractmethod
    def data(self) -> bytes:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def from_data(cls: type[Self], data: bytes) -> Self:
        raise NotImplementedError()


class MocketBaseResponse(ABC):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(data='{self.data!r}')"

    @property
    @abstractmethod
    def data(self) -> bytes:
        raise NotImplementedError()


class MocketBaseEntry(ABC):
    request_cls: ClassVar[type[MocketBaseRequest]]
    response_cls: ClassVar[type[MocketBaseResponse]]

    def __init__(
        self,
        address: Address,
        responses: Sequence[MocketBaseResponse | Exception],
    ) -> None:
        self._address = address
        self._responses = responses
        self._served_response = False
        self._current_response_index = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(address={self.address})"

    @property
    def address(self) -> Address:
        return self._address

    @property
    def responses(self) -> Sequence[MocketBaseResponse | Exception]:
        return self._responses

    @property
    def served_response(self) -> bool:
        return self._served_response

    def can_handle(self, data: bytes) -> bool:
        return True

    def collect(self, data: bytes) -> bool:
        request = self.request_cls.from_data(data)
        Mocket.collect(request)
        return True

    def get_response(self) -> bytes:
        response = self._responses[self._current_response_index]

        self._served_response = True

        self._current_response_index = min(
            self._current_response_index + 1,
            len(self._responses) - 1,
        )

        if isinstance(response, BaseException):
            raise response

        return response.data
