import os
import sys
import shlex

import six

PY2 = sys.version_info[0] == 2
if PY2:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from urlparse import urlsplit, parse_qs
    FileNotFoundError = IOError
else:
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit, parse_qs
    FileNotFoundError = FileNotFoundError

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

text_type = six.text_type
byte_type = six.binary_type
basestring = six.string_types

encoding = os.getenv("MOCKET_ENCODING", 'utf-8')


def encode_to_bytes(s, charset=encoding):
    if isinstance(s, text_type):
        s = s.encode(charset)
    return byte_type(s)


def decode_from_bytes(s, charset=encoding):
    if isinstance(s, byte_type):
        s = s.decode(charset)
    return text_type(s)


def shsplit(s):
    if PY2:
        s = encode_to_bytes(s)
    else:
        s = decode_from_bytes(s)
    return shlex.split(s)
