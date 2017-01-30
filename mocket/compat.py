import sys
import shlex
import six

PY2 = sys.version_info[0] == 2
if PY2:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from urlparse import urlsplit, parse_qs

else:
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit, parse_qs

text_type = six.text_type
byte_type = six.binary_type
basestring = six.string_types

encoding = 'utf-8'


def encode_utf8(s):
    if isinstance(s, text_type):
        s = s.encode(encoding)
    return byte_type(s)


def decode_utf8(s):
    if isinstance(s, byte_type):
        s = s.decode(encoding)
    return text_type(s)


def shsplit(s):
    if PY2:
        s = encode_utf8(s)
    else:
        s = decode_utf8(s)
    return shlex.split(s)
