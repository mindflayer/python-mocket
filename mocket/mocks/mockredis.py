"""Redis mocking implementation for Mocket."""

from __future__ import annotations

from itertools import chain
from typing import Any

from mocket.compat import (
    decode_from_bytes,
    encode_to_bytes,
    shsplit,
)
from mocket.entry import MocketEntry
from mocket.mocket import Mocket
from mocket.types import Address


class Request:
    """Redis request wrapper."""

    def __init__(self, data: bytes) -> None:
        """Initialize a Redis request.

        Args:
            data: Raw Redis command data
        """
        self.data = data


class Response:
    """Redis response wrapper."""

    def __init__(self, data: Any = None) -> None:
        """Initialize a Redis response.

        Args:
            data: Response data (will be "redisize"d)
        """
        self.data = Redisizer.redisize(data or OK)


class Redisizer(bytes):
    """Convert Python types to Redis protocol format."""

    @staticmethod
    def tokens(iterable: list[Any]) -> list[bytes]:
        """Convert an iterable to Redis tokens.

        Args:
            iterable: List of items to convert

        Returns:
            List of Redis protocol bytes
        """
        iterable = [encode_to_bytes(x) for x in iterable]
        return [f"*{len(iterable)}".encode()] + list(
            chain(*zip([f"${len(x)}".encode() for x in iterable], iterable))
        )

    @staticmethod
    def redisize(data: Any) -> Redisizer:
        """Convert Python data to Redis protocol format.

        Args:
            data: Python data to convert

        Returns:
            Redisizer bytes
        """

        def get_conversion(t: type) -> Any:
            return {
                dict: lambda x: b"\r\n".join(
                    Redisizer.tokens(list(chain(*tuple(x.items()))))
                ),
                int: lambda x: f":{x}".encode(),
                str: lambda x: "${}\r\n{}".format(len(x.encode("utf-8")), x).encode(
                    "utf-8"
                ),
                list: lambda x: b"\r\n".join(Redisizer.tokens(x)),
            }[t]

        if isinstance(data, Redisizer):
            return data
        if isinstance(data, bytes):
            data = decode_from_bytes(data)
        return Redisizer(get_conversion(data.__class__)(data) + b"\r\n")

    @staticmethod
    def command(description: str, _type: str = "+") -> Redisizer:
        """Create a Redis command response.

        Args:
            description: Response description
            _type: Response type prefix (+, -, :, $, *)

        Returns:
            Formatted Redis response
        """
        return Redisizer("{}{}{}".format(_type, description, "\r\n").encode("utf-8"))

    @staticmethod
    def error(description: str) -> Redisizer:
        """Create a Redis error response.

        Args:
            description: Error description

        Returns:
            Formatted Redis error response
        """
        return Redisizer.command(description, _type="-")


OK = Redisizer.command("OK")
QUEUED = Redisizer.command("QUEUED")
ERROR = Redisizer.error


class Entry(MocketEntry):
    """Redis entry for matching and responding to Redis commands."""

    request_cls = Request
    response_cls = Response

    def __init__(
        self, addr: Address | None, command: str, responses: list[Any]
    ) -> None:
        """Initialize a Redis entry.

        Args:
            addr: (host, port) tuple or None for default
            command: Redis command string to match
            responses: List of responses to cycle through
        """
        super().__init__(addr or ("localhost", 6379), responses)
        d = shsplit(command)
        d[0] = d[0].upper()
        self.command = Redisizer.tokens(d)

    def can_handle(self, data: bytes) -> bool:
        """Check if this entry can handle the given command.

        Args:
            data: Raw Redis command data

        Returns:
            True if this entry matches the command
        """
        return data.splitlines() == self.command

    @classmethod
    def register(cls, addr: Address | None, command: str, *responses: Any) -> None:
        """Register a Redis entry.

        Args:
            addr: (host, port) tuple or None for default
            command: Redis command to match
            *responses: Responses to cycle through
        """
        responses = [
            r if isinstance(r, BaseException) else cls.response_cls(r)
            for r in responses
        ]
        Mocket.register(cls(addr, command, responses))

    @classmethod
    def register_response(
        cls, command: str, response: Any, addr: Address | None = None
    ) -> None:
        """Register a single response for a command.

        Args:
            command: Redis command to match
            response: Response to return
            addr: (host, port) tuple or None for default
        """
        cls.register(addr, command, response)

    @classmethod
    def register_responses(
        cls, command: str, responses: list[Any], addr: Address | None = None
    ) -> None:
        """Register multiple responses for a command.

        Args:
            command: Redis command to match
            responses: List of responses to cycle through
            addr: (host, port) tuple or None for default
        """
        cls.register(addr, command, *responses)
