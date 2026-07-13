"""Mocket SSL context implementation."""

from __future__ import annotations

from typing import Any

from mocket.mocket import Mocket
from mocket.socket import MocketSocket
from mocket.ssl.socket import MocketSSLSocket


class _MocketSSLContext:
    """Mock SSL context for Python 3.6 and newer."""

    class FakeSetter(int):
        """Descriptor that ignores assignment."""

        def __set__(self, *args: Any) -> None:
            """Ignore any assignment attempts."""
            pass

    minimum_version = FakeSetter()
    options = FakeSetter()
    verify_mode = FakeSetter()
    verify_flags = FakeSetter()


class MocketSSLContext(_MocketSSLContext):
    """Mock SSL context that wraps sockets in MocketSSLSocket."""

    DUMMY_METHODS: tuple = (
        "load_default_certs",
        "load_verify_locations",
        "set_alpn_protocols",
        "set_ciphers",
        "set_default_verify_paths",
    )
    sock: MocketSocket | None = None
    post_handshake_auth: bool | None = None
    _check_hostname: bool = False

    @property
    def check_hostname(self) -> bool:
        """Get the check_hostname setting.

        Returns:
            Always False (mock implementation)
        """
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, _: bool) -> None:
        """Set the check_hostname setting (mocked).

        Args:
            _: Value (ignored, always set to False)
        """
        self._check_hostname = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the SSL context.

        Args:
            *args: Positional arguments (ignored)
            **kwargs: Keyword arguments (ignored)
        """
        self._set_dummy_methods()

    def _set_dummy_methods(self) -> None:
        """Set all dummy methods that do nothing."""

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
        """Wrap a socket in an SSL socket.

        Args:
            sock: Socket to wrap
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            MocketSSLSocket instance
        """
        return MocketSSLSocket._create(sock, *args, **kwargs)

    def wrap_bio(
        self,
        incoming: Any,
        outgoing: Any,
        server_side: bool = False,
        server_hostname: str | bytes | None = None,
    ) -> MocketSSLSocket:
        """Wrap BIO objects in an SSL socket (mock implementation).

        Args:
            incoming: Incoming BIO (_ssl.MemoryBIO)
            outgoing: Outgoing BIO (_ssl.MemoryBIO)
            server_side: Whether this is server side
            server_hostname: Server hostname

        Returns:
            MocketSSLSocket instance
        """
        ssl_obj = MocketSSLSocket()
        if isinstance(server_hostname, bytes):
            hostname = server_hostname.decode("utf-8", errors="replace")
        else:
            hostname = server_hostname

        current_address = Mocket._address
        if isinstance(current_address, tuple) and len(current_address) == 2:
            current_host, current_port = current_address
        else:
            current_host, current_port = None, None

        effective_host = hostname if hostname is not None else current_host
        ssl_obj._host = effective_host
        if current_port is not None:
            ssl_obj._port = current_port
        if effective_host is not None and current_port is not None:
            ssl_obj._address = (effective_host, current_port)
        return ssl_obj


def mock_wrap_socket(
    sock: MocketSocket,
    *args: Any,
    **kwargs: Any,
) -> MocketSSLSocket:
    """Mock ssl.wrap_socket function.

    Args:
        sock: Socket to wrap
        *args: Additional arguments
        **kwargs: Additional keyword arguments

    Returns:
        MocketSSLSocket instance
    """
    context = MocketSSLContext()
    return context.wrap_socket(sock, *args, **kwargs)
