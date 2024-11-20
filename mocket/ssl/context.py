from __future__ import annotations

import contextlib
import ssl
from typing import Any

import urllib3.util.ssl_

from mocket.socket import MocketSocket
from mocket.ssl.socket import MocketSSLSocket

true_ssl_context = ssl.SSLContext

true_ssl_wrap_socket = None
true_urllib3_ssl_wrap_socket = urllib3.util.ssl_.ssl_wrap_socket
true_urllib3_wrap_socket = None

with contextlib.suppress(ImportError):
    # from Py3.12 it's only under SSLContext
    from ssl import wrap_socket as ssl_wrap_socket

    true_ssl_wrap_socket = ssl_wrap_socket

with contextlib.suppress(ImportError):
    from urllib3.util.ssl_ import wrap_socket as urllib3_wrap_socket

    true_urllib3_wrap_socket = urllib3_wrap_socket


class SuperFakeSSLContext:
    """For Python 3.6 and newer."""

    class FakeSetter(int):
        def __set__(self, *args: Any) -> None:
            pass

    minimum_version = FakeSetter()
    options = FakeSetter()
    verify_mode = FakeSetter()
    verify_flags = FakeSetter()


class FakeSSLContext(SuperFakeSSLContext):
    DUMMY_METHODS = (
        "load_default_certs",
        "load_verify_locations",
        "set_alpn_protocols",
        "set_ciphers",
        "set_default_verify_paths",
    )
    sock = None
    post_handshake_auth = None
    _check_hostname = False

    @property
    def check_hostname(self) -> bool:
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, _: bool) -> None:
        self._check_hostname = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._set_dummy_methods()

    def _set_dummy_methods(self) -> None:
        def dummy_method(*args: Any, **kwargs: Any) -> Any:
            pass

        for m in self.DUMMY_METHODS:
            setattr(self, m, dummy_method)

    @staticmethod
    def wrap_socket(sock: MocketSocket, *args: Any, **kwargs: Any) -> MocketSSLSocket:
        ssl_socket = MocketSSLSocket()
        ssl_socket._original_socket = sock

        ssl_socket._true_socket = true_urllib3_ssl_wrap_socket(
            sock._true_socket,
            **kwargs,
        )
        ssl_socket._kwargs = kwargs

        ssl_socket._timeout = sock._timeout

        ssl_socket._host = sock._host
        ssl_socket._port = sock._port
        ssl_socket._address = sock._address

        ssl_socket._io = sock._io
        ssl_socket._entry = sock._entry

        return ssl_socket

    @staticmethod
    def wrap_bio(
        incoming: Any,  # _ssl.MemoryBIO
        outgoing: Any,  # _ssl.MemoryBIO
        server_side: bool = False,
        server_hostname: str | bytes | None = None,
    ) -> MocketSSLSocket:
        ssl_obj = MocketSSLSocket()
        ssl_obj._host = server_hostname
        return ssl_obj
