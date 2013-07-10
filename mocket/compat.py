import sys
import shlex
PY2 = sys.version_info[0] == 2
if PY2:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from urlparse import urlsplit, parse_qs
    text_type = unicode
    byte_type = str
else:
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit, parse_qs
    text_type = str
    byte_type = bytes


def encode_utf8(s):
    if isinstance(s, text_type):
        s = s.encode('utf-8')
    return byte_type(s)


def decode_utf8(s):
    if isinstance(s, byte_type):
        s = s.decode("utf-8")
    return text_type(s)


def shsplit(s):
    if PY2:
        s = encode_utf8(s)
    else:
        s = decode_utf8(s)
    return shlex.split(s)
