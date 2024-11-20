from __future__ import annotations

import os
import socket
import ssl

import urllib3
from urllib3.connection import match_hostname as urllib3_match_hostname
from urllib3.util.ssl_ import ssl_wrap_socket as urllib3_ssl_wrap_socket

try:
    from urllib3.util.ssl_ import wrap_socket as urllib3_wrap_socket
except ImportError:
    urllib3_wrap_socket = None


try:  # pragma: no cover
    from urllib3.contrib.pyopenssl import extract_from_urllib3, inject_into_urllib3

    pyopenssl_override = True
except ImportError:
    pyopenssl_override = False

true_socket = socket.socket
true_create_connection = socket.create_connection
true_gethostbyname = socket.gethostbyname
true_gethostname = socket.gethostname
true_getaddrinfo = socket.getaddrinfo
true_socketpair = socket.socketpair
true_ssl_wrap_socket = getattr(
    ssl, "wrap_socket", None
)  # from Py3.12 it's only under SSLContext
true_ssl_socket = ssl.SSLSocket
true_ssl_context = ssl.SSLContext
true_inet_pton = socket.inet_pton
true_urllib3_wrap_socket = urllib3_wrap_socket
true_urllib3_ssl_wrap_socket = urllib3_ssl_wrap_socket
true_urllib3_match_hostname = urllib3_match_hostname


def enable(
    namespace: str | None = None,
    truesocket_recording_dir: str | None = None,
    recording_ignored_headers: list[str] | None = None,
) -> None:
    from mocket.mocket import Mocket
    from mocket.socket import MocketSocket, create_connection, socketpair
    from mocket.ssl import FakeSSLContext

    Mocket._namespace = namespace
    Mocket._truesocket_recording_dir = truesocket_recording_dir
    Mocket._recording_ignored_headers = recording_ignored_headers or []

    if truesocket_recording_dir and not os.path.isdir(truesocket_recording_dir):
        # JSON dumps will be saved here
        raise AssertionError

    socket.socket = socket.__dict__["socket"] = MocketSocket
    socket._socketobject = socket.__dict__["_socketobject"] = MocketSocket
    socket.SocketType = socket.__dict__["SocketType"] = MocketSocket
    socket.create_connection = socket.__dict__["create_connection"] = create_connection
    socket.gethostname = socket.__dict__["gethostname"] = lambda: "localhost"
    socket.gethostbyname = socket.__dict__["gethostbyname"] = lambda host: "127.0.0.1"
    socket.getaddrinfo = socket.__dict__["getaddrinfo"] = (
        lambda host, port, family=None, socktype=None, proto=None, flags=None: [
            (2, 1, 6, "", (host, port))
        ]
    )
    socket.socketpair = socket.__dict__["socketpair"] = socketpair
    ssl.wrap_socket = ssl.__dict__["wrap_socket"] = FakeSSLContext.wrap_socket
    ssl.SSLContext = ssl.__dict__["SSLContext"] = FakeSSLContext
    socket.inet_pton = socket.__dict__["inet_pton"] = lambda family, ip: bytes(
        "\x7f\x00\x00\x01", "utf-8"
    )
    urllib3.util.ssl_.wrap_socket = urllib3.util.ssl_.__dict__["wrap_socket"] = (
        FakeSSLContext.wrap_socket
    )
    urllib3.util.ssl_.ssl_wrap_socket = urllib3.util.ssl_.__dict__[
        "ssl_wrap_socket"
    ] = FakeSSLContext.wrap_socket
    urllib3.util.ssl_wrap_socket = urllib3.util.__dict__["ssl_wrap_socket"] = (
        FakeSSLContext.wrap_socket
    )
    urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
        "ssl_wrap_socket"
    ] = FakeSSLContext.wrap_socket
    urllib3.connection.match_hostname = urllib3.connection.__dict__[
        "match_hostname"
    ] = lambda *args: None
    if pyopenssl_override:  # pragma: no cover
        # Take out the pyopenssl version - use the default implementation
        extract_from_urllib3()


def disable() -> None:
    from mocket.mocket import Mocket

    socket.socket = socket.__dict__["socket"] = true_socket
    socket._socketobject = socket.__dict__["_socketobject"] = true_socket
    socket.SocketType = socket.__dict__["SocketType"] = true_socket
    socket.create_connection = socket.__dict__["create_connection"] = (
        true_create_connection
    )
    socket.gethostname = socket.__dict__["gethostname"] = true_gethostname
    socket.gethostbyname = socket.__dict__["gethostbyname"] = true_gethostbyname
    socket.getaddrinfo = socket.__dict__["getaddrinfo"] = true_getaddrinfo
    socket.socketpair = socket.__dict__["socketpair"] = true_socketpair
    if true_ssl_wrap_socket:
        ssl.wrap_socket = ssl.__dict__["wrap_socket"] = true_ssl_wrap_socket
    ssl.SSLContext = ssl.__dict__["SSLContext"] = true_ssl_context
    socket.inet_pton = socket.__dict__["inet_pton"] = true_inet_pton
    urllib3.util.ssl_.wrap_socket = urllib3.util.ssl_.__dict__["wrap_socket"] = (
        true_urllib3_wrap_socket
    )
    urllib3.util.ssl_.ssl_wrap_socket = urllib3.util.ssl_.__dict__[
        "ssl_wrap_socket"
    ] = true_urllib3_ssl_wrap_socket
    urllib3.util.ssl_wrap_socket = urllib3.util.__dict__["ssl_wrap_socket"] = (
        true_urllib3_ssl_wrap_socket
    )
    urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
        "ssl_wrap_socket"
    ] = true_urllib3_ssl_wrap_socket
    urllib3.connection.match_hostname = urllib3.connection.__dict__[
        "match_hostname"
    ] = true_urllib3_match_hostname
    Mocket.reset()
    if pyopenssl_override:  # pragma: no cover
        # Put the pyopenssl version back in place
        inject_into_urllib3()
