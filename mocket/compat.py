from __future__ import annotations

import codecs
import os
import shlex
from typing import Final

import puremagic

ENCODING: Final[str] = os.getenv("MOCKET_ENCODING", "utf-8")


def encode_to_bytes(s: str | bytes, encoding: str = ENCODING) -> bytes:
    """Encode a string or bytes to bytes.

    Args:
        s: String or bytes to encode
        encoding: Encoding to use (default: utf-8 or MOCKET_ENCODING env var)

    Returns:
        Encoded bytes
    """
    if isinstance(s, str):
        s = s.encode(encoding)
    return bytes(s)


def decode_from_bytes(s: str | bytes, encoding: str = ENCODING) -> str:
    """Decode bytes or string to string.

    Args:
        s: String or bytes to decode
        encoding: Encoding to use (default: utf-8 or MOCKET_ENCODING env var)

    Returns:
        Decoded string
    """
    if isinstance(s, bytes):
        s = codecs.decode(s, encoding, "ignore")
    return str(s)


def shsplit(s: str | bytes) -> list[str]:
    """Split a shell command string into arguments.

    Args:
        s: Shell command string or bytes

    Returns:
        List of shell command arguments
    """
    s = decode_from_bytes(s)
    return shlex.split(s)


def do_the_magic(body: bytes) -> str:
    """Detect MIME type of binary data using puremagic.

    Args:
        body: Binary data to analyze

    Returns:
        MIME type string
    """
    try:
        magic = puremagic.magic_string(body)
    except puremagic.PureError:
        magic = []
    return magic[0].mime_type if len(magic) else "application/octet-stream"
