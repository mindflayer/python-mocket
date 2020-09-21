import codecs
import os
import shlex
import sys
from socket import error as sock_error

import six

encoding = os.getenv("MOCKET_ENCODING", "utf-8")

text_type = six.text_type
byte_type = six.binary_type
basestring = six.string_types

PY2 = sys.version_info[0] == 2
if PY2:
    import collections as collections_abc
    from BaseHTTPServer import BaseHTTPRequestHandler
    from urlparse import urlsplit, parse_qs, unquote

    def unquote_utf8(qs):
        if isinstance(qs, text_type):
            qs = qs.encode(encoding)
        s = unquote(qs)
        if isinstance(s, byte_type):
            return s.decode(encoding)
        else:
            return s

    FileNotFoundError = IOError
    BlockingIOError = sock_error
else:
    import collections.abc as collections_abc
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit, parse_qs, unquote as unquote_utf8

    FileNotFoundError = FileNotFoundError
    BlockingIOError = BlockingIOError

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


def encode_to_bytes(s, encoding=encoding):
    if isinstance(s, text_type):
        s = s.encode(encoding)
    return byte_type(s)


def decode_from_bytes(s, encoding=encoding):
    if isinstance(s, byte_type):
        s = codecs.decode(s, encoding, "ignore")
    return text_type(s)


def shsplit(s):
    if PY2:
        s = encode_to_bytes(s)
    else:
        s = decode_from_bytes(s)
    return shlex.split(s)


def do_the_magic(lib_magic, body):
    if hasattr(lib_magic, "from_buffer"):
        # PyPI python-magic
        return lib_magic.from_buffer(body, mime=True)
    else:
        # file's builtin python wrapper
        # used by https://www.archlinux.org/packages/community/any/python-mocket/
        _magic = lib_magic.open(lib_magic.MAGIC_MIME_TYPE)
        _magic.load()
        return _magic.buffer(body)
