import contextlib
import errno
import gzip
import hashlib
import json
import logging
import os
import re
import select
import socket
import ssl
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError

from mocket.compat import decode_from_bytes, encode_to_bytes, ENCODING
from mocket.inject import (
    true_gethostbyname,
    true_socket,
    true_urllib3_ssl_wrap_socket,
)
from mocket.io import MocketSocketCore
from mocket.mocket import Mocket
from mocket.mode import MocketMode
from mocket.utils import hexdump, hexload

logger = logging.getLogger(__name__)
xxh32 = None
try:
    from xxhash import xxh32
except ImportError:  # pragma: no cover
    with contextlib.suppress(ImportError):
        from xxhash_cffi import xxh32
hasher = xxh32 or hashlib.md5


def create_connection(address, timeout=None, source_address=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout:
        s.settimeout(timeout)
    s.connect(address)
    return s


def socketpair(*args, **kwargs):
    """Returns a real socketpair() used by asyncio loop for supporting calls made by fastapi and similar services."""
    import _socket

    return _socket.socketpair(*args, **kwargs)


def _hash_request(h, req):
    return h(encode_to_bytes("".join(sorted(req.split("\r\n"))))).hexdigest()


class MocketSocket:
    timeout = None
    _fd = None
    family = None
    type = None
    proto = None
    _host = None
    _port = None
    _address = None
    cipher = lambda s: ("ADH", "AES256", "SHA")
    compression = lambda s: ssl.OP_NO_COMPRESSION
    _mode = None
    _bufsize = None
    _secure_socket = False
    _did_handshake = False
    _sent_non_empty_bytes = False
    _io = None

    def __init__(
        self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, **kwargs
    ):
        self.true_socket = true_socket(family, type, proto)
        self._buflen = 65536
        self._entry = None
        self.family = int(family)
        self.type = int(type)
        self.proto = int(proto)
        self._truesocket_recording_dir = None
        self.kwargs = kwargs

    def __str__(self):
        return f"({self.__class__.__name__})(family={self.family} type={self.type} protocol={self.proto})"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def io(self):
        if self._io is None:
            self._io = MocketSocketCore((self._host, self._port))
        return self._io

    def fileno(self):
        address = (self._host, self._port)
        r_fd, _ = Mocket.get_pair(address)
        if not r_fd:
            r_fd, w_fd = os.pipe()
            Mocket.set_pair(address, (r_fd, w_fd))
        return r_fd

    def gettimeout(self):
        return self.timeout

    def setsockopt(self, family, type, proto):
        self.family = family
        self.type = type
        self.proto = proto

        if self.true_socket:
            self.true_socket.setsockopt(family, type, proto)

    def settimeout(self, timeout):
        self.timeout = timeout

    @staticmethod
    def getsockopt(level, optname, buflen=None):
        return socket.SOCK_STREAM

    def do_handshake(self):
        self._did_handshake = True

    def getpeername(self):
        return self._address

    def setblocking(self, block):
        self.settimeout(None) if block else self.settimeout(0.0)

    def getblocking(self):
        return self.gettimeout() is None

    def getsockname(self):
        return socket.gethostbyname(self._address[0]), self._address[1]

    def getpeercert(self, *args, **kwargs):
        if not (self._host and self._port):
            self._address = self._host, self._port = Mocket._address

        now = datetime.now()
        shift = now + timedelta(days=30 * 12)
        return {
            "notAfter": shift.strftime("%b %d %H:%M:%S GMT"),
            "subjectAltName": (
                ("DNS", f"*.{self._host}"),
                ("DNS", self._host),
                ("DNS", "*"),
            ),
            "subject": (
                (("organizationName", f"*.{self._host}"),),
                (("organizationalUnitName", "Domain Control Validated"),),
                (("commonName", f"*.{self._host}"),),
            ),
        }

    def unwrap(self):
        return self

    def write(self, data):
        return self.send(encode_to_bytes(data))

    def connect(self, address):
        self._address = self._host, self._port = address
        Mocket._address = address

    def makefile(self, mode="r", bufsize=-1):
        self._mode = mode
        self._bufsize = bufsize
        return self.io

    def get_entry(self, data):
        return Mocket.get_entry(self._host, self._port, data)

    def sendall(self, data, entry=None, *args, **kwargs):
        if entry is None:
            entry = self.get_entry(data)

        if entry:
            consume_response = entry.collect(data)
            response = entry.get_response() if consume_response is not False else None
        else:
            response = self.true_sendall(data, *args, **kwargs)

        if response is not None:
            self.io.seek(0)
            self.io.write(response)
            self.io.truncate()
            self.io.seek(0)

    def read(self, buffersize):
        rv = self.io.read(buffersize)
        if rv:
            self._sent_non_empty_bytes = True
        if self._did_handshake and not self._sent_non_empty_bytes:
            raise ssl.SSLWantReadError("The operation did not complete (read)")
        return rv

    def recv_into(self, buffer, buffersize=None, flags=None):
        if hasattr(buffer, "write"):
            return buffer.write(self.read(buffersize))
        # buffer is a memoryview
        data = self.read(buffersize)
        if data:
            buffer[: len(data)] = data
        return len(data)

    def recv(self, buffersize, flags=None):
        r_fd, _ = Mocket.get_pair((self._host, self._port))
        if r_fd:
            return os.read(r_fd, buffersize)
        data = self.read(buffersize)
        if data:
            return data
        # used by Redis mock
        exc = BlockingIOError()
        exc.errno = errno.EWOULDBLOCK
        exc.args = (0,)
        raise exc

    def true_sendall(self, data, *args, **kwargs):
        if not MocketMode().is_allowed((self._host, self._port)):
            MocketMode.raise_not_allowed()

        req = decode_from_bytes(data)
        # make request unique again
        req_signature = _hash_request(hasher, req)
        # port should be always a string
        port = str(self._port)

        # prepare responses dictionary
        responses = {}

        if Mocket.get_truesocket_recording_dir():
            path = os.path.join(
                Mocket.get_truesocket_recording_dir(),
                Mocket.get_namespace() + ".json",
            )
            # check if there's already a recorded session dumped to a JSON file
            try:
                with open(path) as f:
                    responses = json.load(f)
            # if not, create a new dictionary
            except (FileNotFoundError, JSONDecodeError):
                pass

        try:
            try:
                response_dict = responses[self._host][port][req_signature]
            except KeyError:
                if hasher is not hashlib.md5:
                    # Fallback for backwards compatibility
                    req_signature = _hash_request(hashlib.md5, req)
                    response_dict = responses[self._host][port][req_signature]
                else:
                    raise
        except KeyError:
            # preventing next KeyError exceptions
            responses.setdefault(self._host, {})
            responses[self._host].setdefault(port, {})
            responses[self._host][port].setdefault(req_signature, {})
            response_dict = responses[self._host][port][req_signature]

        # try to get the response from the dictionary
        try:
            response = response_dict["response"]

            if Mocket.get_use_hex_encoding():
                encoded_response = hexload(response)
            else:
                headers, body = response.split("\r\n\r\n", 1)

                headers_bytes = headers.encode(ENCODING)
                body_bytes = body.encode(ENCODING)

                if "content-encoding: gzip" in headers.lower():
                    body_bytes = gzip.compress(body_bytes)

                encoded_response = headers_bytes + b"\r\n\r\n" + body_bytes
        # if not available, call the real sendall
        except KeyError:
            host, port = self._host, self._port
            host = true_gethostbyname(host)

            if isinstance(self.true_socket, true_socket) and self._secure_socket:
                self.true_socket = true_urllib3_ssl_wrap_socket(
                    self.true_socket,
                    **self.kwargs,
                )

            with contextlib.suppress(OSError, ValueError):
                # already connected
                self.true_socket.connect((host, port))
            self.true_socket.sendall(data, *args, **kwargs)
            encoded_response = b""
            # https://github.com/kennethreitz/requests/blob/master/tests/testserver/server.py#L12
            while True:
                more_to_read = select.select([self.true_socket], [], [], 0.1)[0]
                if not more_to_read and encoded_response:
                    break
                new_content = self.true_socket.recv(self._buflen)
                if not new_content:
                    break
                encoded_response += new_content

            # dump the resulting dictionary to a JSON file
            if Mocket.get_truesocket_recording_dir():
                # update the dictionary with request and response lines
                response_dict["request"] = req

                if Mocket.get_use_hex_encoding():
                    response_dict["response"] = hexdump(encoded_response)
                else:
                    headers, body = encoded_response.split(b"\r\n\r\n", 1)

                    if b"content-encoding: gzip" in headers.lower():
                        body = gzip.decompress(body)

                    response_dict["response"] = (headers + b"\r\n\r\n" + body).decode(
                        ENCODING
                    )

                with open(path, mode="w") as f:
                    f.write(
                        decode_from_bytes(
                            json.dumps(responses, indent=4, sort_keys=True)
                        )
                    )

        # response back to .sendall() which writes it to the Mocket socket and flush the BytesIO
        return encoded_response

    def send(self, data, *args, **kwargs):  # pragma: no cover
        entry = self.get_entry(data)
        if not entry or (entry and self._entry != entry):
            kwargs["entry"] = entry
            self.sendall(data, *args, **kwargs)
        else:
            req = Mocket.last_request()
            if hasattr(req, "add_data"):
                req.add_data(data)
        self._entry = entry
        return len(data)

    def close(self):
        if self.true_socket and not self.true_socket._closed:
            self.true_socket.close()
        self._fd = None

    def __getattr__(self, name):
        """Do nothing catchall function, for methods like shutdown()"""

        def do_nothing(*args, **kwargs):
            pass

        return do_nothing
