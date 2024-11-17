from __future__ import annotations

import ssl
from typing import Any

from mocket.socket import MocketSocket

true_ssl_context = ssl.SSLContext


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
    def wrap_socket(sock: MocketSocket, *args: Any, **kwargs: Any) -> MocketSocket:
        sock._kwargs = kwargs
        sock._secure_socket = True
        return sock

    @staticmethod
    def wrap_bio(
        incoming: Any,  # _ssl.MemoryBIO
        outgoing: Any,  # _ssl.MemoryBIO
        server_side: bool = False,
        server_hostname: str | bytes | None = None,
    ) -> MocketSocket:
        ssl_obj = MocketSocket()
        ssl_obj._host = server_hostname
        return ssl_obj
