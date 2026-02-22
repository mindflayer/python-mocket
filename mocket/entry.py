"""Mocket entry base class for registering mock responses."""

from __future__ import annotations

import collections.abc
from typing import Any

from mocket.compat import encode_to_bytes
from mocket.mocket import Mocket


class MocketEntry:
    """Base class for Mocket entries that match requests and return responses."""

    class Response(bytes):
        """Response wrapper class that extends bytes."""

        @property
        def data(self) -> bytes:
            """Get the response data."""
            return self

    response_index: int = 0
    request_cls: type = bytes
    response_cls: type = Response
    responses: list | None = None
    _served: bool | None = None

    def __init__(self, location: tuple, responses: Any) -> None:
        """Initialize a Mocket entry.

        Args:
            location: Tuple of (host, port)
            responses: Single response or list of responses to cycle through
        """
        self._served = False
        self.location = location

        if not isinstance(responses, collections.abc.Iterable):
            responses = [responses]

        if not responses:
            self.responses = [self.response_cls(encode_to_bytes(""))]
        else:
            self.responses = []
            for r in responses:
                if not isinstance(r, BaseException) and not getattr(r, "data", False):
                    if isinstance(r, str):
                        r = encode_to_bytes(r)
                    r = self.response_cls(r)
                self.responses.append(r)

    def __repr__(self) -> str:
        """Return a string representation of the entry."""
        return f"{self.__class__.__name__}(location={self.location})"

    @staticmethod
    def can_handle(data: bytes) -> bool:
        """Check if this entry can handle the given request data.

        Args:
            data: Request data to check

        Returns:
            True if this entry can handle the request, False otherwise
        """
        return True

    def collect(self, data: bytes) -> None:
        """Collect the request data in the Mocket singleton.

        Args:
            data: Request data to collect
        """
        req = self.request_cls(data)
        Mocket.collect(req)

    def get_response(self) -> bytes:
        """Get the next response to send.

        Returns:
            Response bytes to send to the client

        Raises:
            BaseException: If a response is an exception, it will be raised
        """
        response = self.responses[self.response_index]
        if self.response_index < len(self.responses) - 1:
            self.response_index += 1

        self._served = True

        if isinstance(response, BaseException):
            raise response

        return response.data
