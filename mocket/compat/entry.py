from __future__ import annotations

from mocket.bytes import MocketBytesEntry, MocketBytesResponse
from mocket.core.types import Address


class Response(MocketBytesResponse):
    def __init__(self, data: bytes | str | bool) -> None:
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, bool):
            data = bytes(data)
        self._data = data


class MocketEntry(MocketBytesEntry):
    def __init__(
        self,
        location: Address,
        responses: list[MocketBytesResponse | Exception | bytes | str | bool]
        | MocketBytesResponse
        | Exception
        | bytes
        | str
        | bool,
    ) -> None:
        if not isinstance(responses, list):
            responses = [responses]

        _responses = []
        for response in responses:
            if not isinstance(response, (MocketBytesResponse, Exception)):
                response = MocketBytesResponse(response)
            _responses.append(response)

        super().__init__(address=location, responses=_responses)
