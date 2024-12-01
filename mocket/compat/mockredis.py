from __future__ import annotations

from typing import Sequence

from mocket.core.mocket import Mocket
from mocket.core.types import Address
from mocket.redis import MocketRedisEntry, MocketRedisResponse

DEFAULT_ADDRESS = ("localhost", 6379)


class Entry(MocketRedisEntry):
    def __init__(
        self,
        addr: Address | None,
        command: str | bytes,
        responses: Sequence[MocketRedisResponse | Exception],
    ) -> None:
        super().__init__(
            address=addr or DEFAULT_ADDRESS,
            command=command,
            responses=responses,
        )

    @property
    def command(self) -> list[bytes]:  # type: ignore[override]
        return self._command_tokens

    @staticmethod
    def _convert_response(
        response: str
        | bytes
        | int
        | list[str]
        | list[bytes]
        | dict[str, str]
        | dict[bytes, bytes]
        | Exception
        | MocketRedisResponse,
    ) -> MocketRedisResponse | Exception:
        if isinstance(response, (MocketRedisResponse, Exception)):
            return response

        return MocketRedisResponse(data=response)

    @classmethod
    def register(
        cls,
        addr: Address | None,
        command: str | bytes,
        *responses: str
        | bytes
        | int
        | list[str]
        | list[bytes]
        | dict[str, str]
        | dict[bytes, bytes]
        | Exception
        | MocketRedisResponse,
    ) -> None:
        cls.register_responses(
            command=command,
            responses=responses,
            addr=addr,
        )

    @classmethod
    def register_response(  # type: ignore[override]
        cls,
        command: str | bytes,
        response: str
        | bytes
        | int
        | list[str]
        | list[bytes]
        | dict[str, str]
        | dict[bytes, bytes]
        | Exception
        | MocketRedisResponse,
        addr: Address | None = None,
    ) -> None:
        response = Entry._convert_response(response)
        entry = cls(
            addr=addr or DEFAULT_ADDRESS,
            command=command,
            responses=[response],
        )
        Mocket.register(entry)

    @classmethod
    def register_responses(  # type: ignore[override]
        cls,
        command: str | bytes,
        responses: Sequence[
            str
            | bytes
            | int
            | list[str]
            | list[bytes]
            | dict[str, str]
            | dict[bytes, bytes]
            | Exception
            | MocketRedisResponse
        ],
        addr: Address | None = None,
    ) -> None:
        _responses = []
        for response in responses:
            response = Entry._convert_response(response)
            _responses.append(response)

        entry = cls(
            addr=addr or DEFAULT_ADDRESS,
            command=command,
            responses=_responses,
        )
        Mocket.register(entry)
