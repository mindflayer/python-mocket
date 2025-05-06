from __future__ import annotations

import binascii
import contextlib
from typing import Any, Callable, Protocol, TypeVar, overload

import decorator
from typing_extensions import ParamSpec

from mocket.compat import decode_from_bytes, encode_to_bytes

_P = ParamSpec("_P")
_R = TypeVar("_R")


class MocketizeDecorator(Protocol):
    """
    This is a generic decorator signature, currently applicable to get_mocketize.

    Decorators can be used as:
    1. A function that transforms func (the parameter) into func1 (the returned object).
    2. A function that takes keyword arguments and returns 1.
    """

    @overload
    def __call__(self, func: Callable[_P, _R], /) -> Callable[_P, _R]: ...

    @overload
    def __call__(
        self, **kwargs: Any
    ) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...


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


def get_mocketize(wrapper_: Callable) -> MocketizeDecorator:
    # trying to support different versions of `decorator`
    with contextlib.suppress(TypeError):
        return decorator.decorator(wrapper_, kwsyntax=True)  # type: ignore[return-value, call-arg, unused-ignore]
    return decorator.decorator(wrapper_)  # type: ignore[return-value]


__all__ = (
    "get_mocketize",
    "hexdump",
    "hexload",
)
