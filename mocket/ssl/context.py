from __future__ import annotations

from typing import Any

from mocket.socket import MocketSocket
from mocket.ssl.socket import MocketSSLSocket


class _MocketSSLContext:
    """For Python 3.6 and newer."""

    class FakeSetter(int):
        def __set__(self, *args: Any) -> None:
            pass

    minimum_version = FakeSetter()
    options = FakeSetter()
    verify_mode = FakeSetter()
    verify_flags = FakeSetter()


class MocketSSLContext(_MocketSSLContext):
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

    def wrap_socket(
        self,
        sock: MocketSocket,
        *args: Any,
        **kwargs: Any,
    ) -> MocketSSLSocket:
        return MocketSSLSocket._create(sock, *args, **kwargs)

    def wrap_bio(
        self,
        incoming: Any,  # _ssl.MemoryBIO
        outgoing: Any,  # _ssl.MemoryBIO
        server_side: bool = False,
        server_hostname: str | bytes | None = None,
    ) -> MocketSSLSocket:
        ssl_obj = MocketSSLSocket()
        ssl_obj._host = server_hostname
        return ssl_obj


def mock_wrap_socket(
    sock: MocketSocket,
    *args: Any,
    **kwargs: Any,
) -> MocketSSLSocket:
    context = MocketSSLContext()
    return context.wrap_socket(sock, *args, **kwargs)
