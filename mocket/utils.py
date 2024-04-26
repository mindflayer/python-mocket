from __future__ import annotations

import binascii
import io
import os
import ssl
from typing import Tuple, Union, Callable, TYPE_CHECKING, TypeVar, Any, ClassVar
from typing_extensions import override

from .compat import decode_from_bytes, encode_to_bytes
from .exceptions import StrictMocketException

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer
    from typing_extensions import NoReturn

SSL_PROTOCOL = ssl.PROTOCOL_TLSv1_2

T = TypeVar("T")

class MocketSocketCore(io.BytesIO):
    @override
    def write(self, content: ReadableBuffer) -> None:  # type: ignore[override] # BytesIO returns int
        super(MocketSocketCore, self).write(content)

        from mocket import Mocket

        if Mocket.r_fd and Mocket.w_fd:
            os.write(Mocket.w_fd, content)


def hexdump(binary_string: bytes)  -> str:
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


def get_mocketize(wrapper_: T) -> T:
    import decorator

    if decorator.__version__ < "5":   # type: ignore[attr-defined] # pragma: no cover
        return decorator.decorator(wrapper_)
    return decorator.decorator(wrapper_, kwsyntax=True)


class MocketMode:
    __shared_state: ClassVar[dict[str, Any]] = {}
    STRICT: ClassVar = None
    STRICT_ALLOWED: ClassVar = None

    def __init__(self) -> None:
        self.__dict__ = self.__shared_state

    def is_allowed(self, location: Union[str, Tuple[str, int]]) -> bool:
        """
        Checks if (`host`, `port`) or at least `host`
        are allowed locationsto perform real `socket` calls
        """
        if not self.STRICT:
            return True
        host, _ = location
        return location in self.STRICT_ALLOWED or host in self.STRICT_ALLOWED

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
