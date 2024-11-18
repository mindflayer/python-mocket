from __future__ import annotations

import contextlib
import errno
import hashlib
import json
import os
import select
import socket
import ssl
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from types import TracebackType
from typing import Any, Type

import urllib3.connection
from typing_extensions import Self

from mocket.compat import decode_from_bytes, encode_to_bytes
from mocket.entry import MocketEntry
from mocket.io import MocketSocketCore
from mocket.mocket import Mocket
from mocket.mode import MocketMode
from mocket.types import (
    Address,
    ReadableBuffer,
    WriteableBuffer,
    _PeerCertRetDictType,
    _RetAddress,
)
from mocket.utils import hexdump, hexload

true_create_connection = socket.create_connection
true_getaddrinfo = socket.getaddrinfo
true_gethostbyname = socket.gethostbyname
true_gethostname = socket.gethostname
true_inet_pton = socket.inet_pton
true_socket = socket.socket
true_socketpair = socket.socketpair
true_urllib3_match_hostname = urllib3.connection.match_hostname


xxh32 = None
try:
    from xxhash import xxh32
except ImportError:  # pragma: no cover
    with contextlib.suppress(ImportError):
        from xxhash_cffi import xxh32
hasher = xxh32 or hashlib.md5


def mock_create_connection(address, timeout=None, source_address=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout:
        s.settimeout(timeout)
    s.connect(address)
    return s


def mock_getaddrinfo(
    host: str,
    port: int,
    family: int = 0,
    type: int = 0,
    proto: int = 0,
    flags: int = 0,
) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(2, 1, 6, "", (host, port))]


def mock_gethostbyname(hostname: str) -> str:
    return "127.0.0.1"


def mock_gethostname() -> str:
    return "localhost"


def mock_inet_pton(address_family: int, ip_string: str) -> bytes:
    return bytes("\x7f\x00\x00\x01", "utf-8")


def mock_socketpair(*args, **kwargs):
    """Returns a real socketpair() used by asyncio loop for supporting calls made by fastapi and similar services."""
    import _socket

    return _socket.socketpair(*args, **kwargs)


def mock_urllib3_match_hostname(*args: Any) -> None:
    return None


def _hash_request(h, req):
    return h(encode_to_bytes("".join(sorted(req.split("\r\n"))))).hexdigest()


class MocketSocket:
    cipher = lambda s: ("ADH", "AES256", "SHA")
    compression = lambda s: ssl.OP_NO_COMPRESSION

    def __init__(
        self,
        family: socket.AddressFamily | int = socket.AF_INET,
        type: socket.SocketKind | int = socket.SOCK_STREAM,
        proto: int = 0,
        fileno: int | None = None,
        **kwargs: Any,
    ) -> None:
        self._family = family
        self._type = type
        self._proto = proto

        self._kwargs = kwargs
        self._true_socket = true_socket(family, type, proto)

        self._buflen = 65536
        self._timeout: float | None = None

        self._secure_socket = False
        self._did_handshake = False
        self._sent_non_empty_bytes = False

        self._host = None
        self._port = None
        self._address = None

        self._io = None
        self._entry = None

    def __str__(self) -> str:
        return f"({self.__class__.__name__})(family={self.family} type={self.type} protocol={self.proto})"

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        type_: Type[BaseException] | None,  # noqa: UP006
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @property
    def family(self) -> int:
        return self._family

    @property
    def type(self) -> int:
        return self._type

    @property
    def proto(self) -> int:
        return self._proto

    @property
    def io(self) -> MocketSocketCore:
        if self._io is None:
            self._io = MocketSocketCore((self._host, self._port))
        return self._io

    def fileno(self) -> int:
        address = (self._host, self._port)
        r_fd, _ = Mocket.get_pair(address)
        if not r_fd:
            r_fd, w_fd = os.pipe()
            Mocket.set_pair(address, (r_fd, w_fd))
        return r_fd

    def gettimeout(self) -> float | None:
        return self._timeout

    # FIXME the arguments here seem wrong. they should be `level: int, optname: int, value: int | ReadableBuffer | None`
    def setsockopt(self, family: int, type: int, proto: int) -> None:
        self._family = family
        self._type = type
        self._proto = proto

        if self._true_socket:
            self._true_socket.setsockopt(family, type, proto)

    def settimeout(self, timeout: float | None) -> None:
        self._timeout = timeout

    @staticmethod
    def getsockopt(level: int, optname: int, buflen: int | None = None) -> int:
        return socket.SOCK_STREAM

    def do_handshake(self) -> None:
        self._did_handshake = True

    def getpeername(self) -> _RetAddress:
        return self._address

    def setblocking(self, block: bool) -> None:
        self.settimeout(None) if block else self.settimeout(0.0)

    def getblocking(self) -> bool:
        return self.gettimeout() is None

    def getsockname(self) -> _RetAddress:
        return true_gethostbyname(self._address[0]), self._address[1]

    def getpeercert(self, binary_form: bool = False) -> _PeerCertRetDictType:
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

    def unwrap(self) -> MocketSocket:
        return self

    def write(self, data: bytes) -> int | None:
        return self.send(encode_to_bytes(data))

    def connect(self, address: Address) -> None:
        self._address = self._host, self._port = address
        Mocket._address = address

    def makefile(self, mode: str = "r", bufsize: int = -1) -> MocketSocketCore:
        return self.io

    def get_entry(self, data: bytes) -> MocketEntry | None:
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

    def read(self, buffersize: int | None = None) -> bytes:
        rv = self.io.read(buffersize)
        if rv:
            self._sent_non_empty_bytes = True
        if self._did_handshake and not self._sent_non_empty_bytes:
            raise ssl.SSLWantReadError("The operation did not complete (read)")
        return rv

    def recv_into(
        self,
        buffer: WriteableBuffer,
        buffersize: int | None = None,
        flags: int | None = None,
    ) -> int:
        if hasattr(buffer, "write"):
            return buffer.write(self.read(buffersize))
        # buffer is a memoryview
        data = self.read(buffersize)
        if data:
            buffer[: len(data)] = data
        return len(data)

    def recv(self, buffersize: int, flags: int | None = None) -> bytes:
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

    def true_sendall(self, data: ReadableBuffer, *args: Any, **kwargs: Any) -> int:
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
            encoded_response = hexload(response_dict["response"])
        # if not available, call the real sendall
        except KeyError:
            host, port = self._host, self._port
            host = true_gethostbyname(host)

            if isinstance(self._true_socket, true_socket) and self._secure_socket:
                from mocket.ssl.context import true_urllib3_ssl_wrap_socket

                self._true_socket = true_urllib3_ssl_wrap_socket(
                    self._true_socket,
                    **self._kwargs,
                )

            with contextlib.suppress(OSError, ValueError):
                # already connected
                self._true_socket.connect((host, port))
            self._true_socket.sendall(data, *args, **kwargs)
            encoded_response = b""
            # https://github.com/kennethreitz/requests/blob/master/tests/testserver/server.py#L12
            while True:
                more_to_read = select.select([self._true_socket], [], [], 0.1)[0]
                if not more_to_read and encoded_response:
                    break
                new_content = self._true_socket.recv(self._buflen)
                if not new_content:
                    break
                encoded_response += new_content

            # dump the resulting dictionary to a JSON file
            if Mocket.get_truesocket_recording_dir():
                # update the dictionary with request and response lines
                response_dict["request"] = req
                response_dict["response"] = hexdump(encoded_response)

                with open(path, mode="w") as f:
                    f.write(
                        decode_from_bytes(
                            json.dumps(responses, indent=4, sort_keys=True)
                        )
                    )

        # response back to .sendall() which writes it to the Mocket socket and flush the BytesIO
        return encoded_response

    def send(
        self,
        data: ReadableBuffer,
        *args: Any,
        **kwargs: Any,
    ) -> int:  # pragma: no cover
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

    def close(self) -> None:
        if self._true_socket and not self._true_socket._closed:
            self._true_socket.close()

    def __getattr__(self, name: str) -> Any:
        """Do nothing catchall function, for methods like shutdown()"""

        def do_nothing(*args: Any, **kwargs: Any) -> Any:
            pass

        return do_nothing
