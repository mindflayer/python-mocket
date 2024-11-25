from __future__ import annotations

import binascii
import ssl
from typing import Callable

from mocket.compat import decode_from_bytes, encode_to_bytes

# NOTE this is here for backwards-compat to keep old import-paths working
from mocket.io import MocketSocketIO as MocketSocketCore

# NOTE this is here for backwards-compat to keep old import-paths working
from mocket.mode import MocketMode

SSL_PROTOCOL = ssl.PROTOCOL_TLSv1_2


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


__all__ = (
    "MocketMode",
    "MocketSocketCore",
    "SSL_PROTOCOL",
    "get_mocketize",
    "hexdump",
    "hexload",
)
