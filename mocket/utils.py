from __future__ import annotations

import binascii
import contextlib
from typing import Callable

import decorator

from mocket.compat import decode_from_bytes, encode_to_bytes


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
    try:
        return encode_to_bytes(binascii.unhexlify(string_no_spaces))
    except binascii.Error as e:
        raise ValueError from e


def get_mocketize(wrapper_: Callable) -> Callable:
    # trying to support different versions of `decorator`
    with contextlib.suppress(TypeError):
        return decorator.decorator(wrapper_, kwsyntax=True)  # type: ignore[call-arg,unused-ignore]
    return decorator.decorator(wrapper_)


__all__ = (
    "get_mocketize",
    "hexdump",
    "hexload",
)
