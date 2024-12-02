from __future__ import annotations

from itertools import chain
from typing import Sequence

from mocket.bytes import MocketBytesRequest, MocketBytesResponse
from mocket.core.compat import encode_to_bytes, shsplit
from mocket.core.entry import MocketBaseEntry
from mocket.core.mocket import Mocket
from mocket.core.types import Address

CRLF = "\r\n"


class MocketRedisCommand(bytes): ...


class Redisizer(bytes):
    @staticmethod
    def tokens(iterable: Sequence[str | bytes]) -> list[bytes]:
        _iterable = [encode_to_bytes(x) for x in iterable]
        return [f"*{len(iterable)}".encode()] + list(
            chain(*zip([f"${len(x)}".encode() for x in _iterable], _iterable))
        )

    @staticmethod
    def redisize(
        data: str
        | bytes
        | int
        | list[str]
        | list[bytes]
        | dict[str, str]
        | dict[bytes, bytes]
        | MocketRedisCommand,
    ) -> bytes:
        if isinstance(data, MocketRedisCommand):
            return data

        if isinstance(data, bytes):
            data = data.decode()

        if isinstance(data, str):
            data_len = len(data.encode())
            data = f"${data_len}{CRLF}{data}".encode()

        elif isinstance(data, int):
            data = f":{data}".encode()

        elif isinstance(data, list):
            tokens = Redisizer.tokens(data)
            data = CRLF.encode().join(tokens)

        elif isinstance(data, dict):
            tokens = Redisizer.tokens(list(chain(*tuple(data.items()))))  # type: ignore[arg-type]
            data = CRLF.encode().join(tokens)

        return data + CRLF.encode()

    @staticmethod
    def command(description: str, _type: str = "+") -> MocketRedisCommand:
        return MocketRedisCommand(f"{_type}{description}{CRLF}".encode())

    @staticmethod
    def error(description: str) -> MocketRedisCommand:
        return Redisizer.command(description, _type="-")


OK = Redisizer.command("OK")
QUEUED = Redisizer.command("QUEUED")
ERROR = Redisizer.error


class MocketRedisRequest(MocketBytesRequest): ...


class MocketRedisResponse(MocketBytesResponse):
    def __init__(
        self,
        data: str
        | bytes
        | int
        | list[str]
        | list[bytes]
        | dict[str, str]
        | dict[bytes, bytes]
        | MocketRedisCommand = OK,
    ) -> None:
        data = Redisizer.redisize(data)
        super().__init__(data=data)


class MocketRedisEntry(MocketBaseEntry):
    request_cls = MocketRedisRequest
    response_cls = MocketRedisResponse

    def __init__(
        self,
        address: Address,
        command: str | bytes,
        responses: Sequence[MocketRedisResponse | Exception],
    ) -> None:
        self._command = command
        self._command_tokens = MocketRedisEntry._tokenize_command(command)

        super().__init__(address=address, responses=responses)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"address={self.address}, "
            f"command='{self.command!r}"
            ")"
        )

    # TODO should this always be str?
    @property
    def command(self) -> str | bytes:
        return self._command

    def can_handle(self, data: bytes) -> bool:
        return data.splitlines() == self._command_tokens

    @staticmethod
    def _tokenize_command(command: str | bytes) -> list[bytes]:
        parts = shsplit(command)
        parts[0] = parts[0].upper()
        return Redisizer.tokens(parts)

    @classmethod
    def register_response(
        cls,
        address: Address,
        command: str | bytes,
        response: MocketRedisResponse | Exception,
    ) -> None:
        entry = cls(
            address=address,
            command=command,
            responses=[response],
        )
        Mocket.register(entry)

    @classmethod
    def register_responses(
        cls,
        address: Address,
        command: str | bytes,
        responses: Sequence[MocketRedisResponse | Exception],
    ) -> None:
        entry = cls(
            address=address,
            command=command,
            responses=responses,
        )
        Mocket.register(entry)
