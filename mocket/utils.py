from __future__ import annotations

import binascii
import io
import os
import ssl
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from .compat import decode_from_bytes, encode_to_bytes
from .exceptions import StrictMocketException

if TYPE_CHECKING:  # pragma: no cover
    from typing import NoReturn


SSL_PROTOCOL = ssl.PROTOCOL_TLSv1_2


class MocketSocketCore(io.BytesIO):
    def __init__(self, address) -> None:
        self._address = address
        super().__init__()

    def write(self, content):
        from mocket import Mocket

        super().write(content)

        _, w_fd = Mocket.get_pair(self._address)
        if w_fd:
            os.write(w_fd, content)


def hexdump(binary_string: bytes) -> str:
    r"""
    >>> hexdump(b"bar foobar foo") == decode_from_bytes(encode_to_bytes("62 61 72 20 66 6F 6F 62 61 72 20 66 6F 6F"))
    True
    """
    bs = decode_from_bytes(binascii.hexlify(binary_string).upper())
    return " ".join(a + b for a, b in zip(bs[::2], bs[1::2]))


def hexload(string: str) -> bytes:
    r"""
    >>> hexload("62 61 72 20 66 6F 6F 62 61 72 20 66 6F 6F") == encode_to_bytes("bar foobar foo")
    True
    """
    string_no_spaces = "".join(string.split())
    return encode_to_bytes(binascii.unhexlify(string_no_spaces))


def get_mocketize(wrapper_: Callable) -> Callable:
    import decorator

    if decorator.__version__ < "5":  # type: ignore[attr-defined] # pragma: no cover
        return decorator.decorator(wrapper_)
    return decorator.decorator(  # type: ignore[call-arg] # kwsyntax
        wrapper_,
        kwsyntax=True,
    )


class MocketMode:
    __shared_state: ClassVar[dict[str, Any]] = {}
    STRICT: ClassVar = None
    STRICT_ALLOWED: ClassVar = None

    def __init__(self) -> None:
        self.__dict__ = self.__shared_state

    def is_allowed(self, location: str | tuple[str, int]) -> bool:
        """
        Checks if (`host`, `port`) or at least `host`
        are allowed locations to perform real `socket` calls
        """
        if not self.STRICT:
            return True

        host_allowed = False
        if isinstance(location, tuple):
            host_allowed = location[0] in self.STRICT_ALLOWED
        return host_allowed or location in self.STRICT_ALLOWED

    @staticmethod
    def raise_not_allowed() -> NoReturn:
        from .mocket import Mocket

        current_entries = [
            (location, "\n    ".join(map(str, entries)))
            for location, entries in Mocket._entries.items()
        ]
        formatted_entries = "\n".join(
            [f"  {location}:\n    {entries}" for location, entries in current_entries]
        )
        raise StrictMocketException(
            "Mocket tried to use the real `socket` module while STRICT mode was active.\n"
            f"Registered entries:\n{formatted_entries}"
        )
