from __future__ import annotations

import codecs
import os
import shlex
from typing import Final

import puremagic

ENCODING: Final[str] = os.getenv("MOCKET_ENCODING", "utf-8")


def encode_to_bytes(s: str | bytes, encoding: str = ENCODING) -> bytes:
    if isinstance(s, str):
        s = s.encode(encoding)
    return bytes(s)


def decode_from_bytes(s: str | bytes, encoding: str = ENCODING) -> str:
    if isinstance(s, bytes):
        s = codecs.decode(s, encoding, "ignore")
    return str(s)


def shsplit(s: str | bytes) -> list[str]:
    s = decode_from_bytes(s)
    return shlex.split(s)


def do_the_magic(body):
    try:
        magic = puremagic.magic_string(body)
    except puremagic.PureError:
        magic = []
    return magic[0].mime_type if len(magic) else "application/octet-stream"
