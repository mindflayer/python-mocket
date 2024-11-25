from __future__ import annotations

import os
import socket
import ssl

import urllib3

try:  # pragma: no cover
    from urllib3.contrib.pyopenssl import extract_from_urllib3, inject_into_urllib3

    pyopenssl_override = True
except ImportError:
    pyopenssl_override = False


def enable(
    namespace: str | None = None,
    truesocket_recording_dir: str | None = None,
    recording_ignored_headers: list[str] | None = None,
) -> None:
    from mocket.mocket import Mocket
    from mocket.socket import (
        MocketSocket,
        mock_create_connection,
        mock_getaddrinfo,
        mock_gethostbyname,
        mock_gethostname,
        mock_inet_pton,
        mock_socketpair,
        mock_urllib3_match_hostname,
    )
    from mocket.ssl.context import MocketSSLContext

    Mocket._namespace = namespace
    Mocket._truesocket_recording_dir = truesocket_recording_dir
    Mocket._recording_ignored_headers = recording_ignored_headers or []

    if truesocket_recording_dir and not os.path.isdir(truesocket_recording_dir):
        # JSON dumps will be saved here
        raise AssertionError

    socket.socket = socket.__dict__["socket"] = MocketSocket
    socket._socketobject = socket.__dict__["_socketobject"] = MocketSocket
    socket.SocketType = socket.__dict__["SocketType"] = MocketSocket
    socket.create_connection = socket.__dict__["create_connection"] = (
        mock_create_connection
    )
    socket.gethostname = socket.__dict__["gethostname"] = mock_gethostname
    socket.gethostbyname = socket.__dict__["gethostbyname"] = mock_gethostbyname
    socket.getaddrinfo = socket.__dict__["getaddrinfo"] = mock_getaddrinfo
    socket.socketpair = socket.__dict__["socketpair"] = mock_socketpair
    ssl.wrap_socket = ssl.__dict__["wrap_socket"] = MocketSSLContext.wrap_socket
    ssl.SSLContext = ssl.__dict__["SSLContext"] = MocketSSLContext
    socket.inet_pton = socket.__dict__["inet_pton"] = mock_inet_pton
    urllib3.util.ssl_.wrap_socket = urllib3.util.ssl_.__dict__["wrap_socket"] = (
        MocketSSLContext.wrap_socket
    )
    urllib3.util.ssl_.ssl_wrap_socket = urllib3.util.ssl_.__dict__[
        "ssl_wrap_socket"
    ] = MocketSSLContext.wrap_socket
    urllib3.util.ssl_wrap_socket = urllib3.util.__dict__["ssl_wrap_socket"] = (
        MocketSSLContext.wrap_socket
    )
    urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
        "ssl_wrap_socket"
    ] = MocketSSLContext.wrap_socket
    urllib3.connection.match_hostname = urllib3.connection.__dict__[
        "match_hostname"
    ] = mock_urllib3_match_hostname
    if pyopenssl_override:  # pragma: no cover
        # Take out the pyopenssl version - use the default implementation
        extract_from_urllib3()


def disable() -> None:
    from mocket.mocket import Mocket
    from mocket.socket import (
        true_create_connection,
        true_getaddrinfo,
        true_gethostbyname,
        true_gethostname,
        true_inet_pton,
        true_socket,
        true_socketpair,
        true_urllib3_match_hostname,
    )
    from mocket.ssl.context import (
        true_ssl_context,
        true_ssl_wrap_socket,
        true_urllib3_ssl_wrap_socket,
        true_urllib3_wrap_socket,
    )

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
