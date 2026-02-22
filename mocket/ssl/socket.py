"""Mocket SSL socket implementation."""

from __future__ import annotations

import ssl
from datetime import datetime, timedelta
from ssl import Options
from typing import Any

from mocket.compat import encode_to_bytes
from mocket.mocket import Mocket
from mocket.socket import MocketSocket
from mocket.types import _PeerCertRetDictType


class MocketSSLSocket(MocketSocket):
    """Mock SSL socket that extends MocketSocket with SSL-specific behavior."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize an SSL socket.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)

        self._did_handshake: bool = False
        self._sent_non_empty_bytes: bool = False
        self._original_socket: MocketSocket = self

    def read(self, buffersize: int | None = None) -> bytes:
        """Read data from the SSL socket.

        Args:
            buffersize: Maximum bytes to read

        Returns:
            Bytes read from the socket

        Raises:
            ssl.SSLWantReadError: If handshake not completed and no data
        """
        rv = self.io.read(buffersize)
        if rv:
            self._sent_non_empty_bytes = True
        if self._did_handshake and not self._sent_non_empty_bytes:
            raise ssl.SSLWantReadError("The operation did not complete (read)")
        return rv

    def write(self, data: bytes) -> int | None:
        """Write data to the SSL socket.

        Args:
            data: Bytes to write

        Returns:
            Number of bytes written
        """
        return self.send(encode_to_bytes(data))

    def do_handshake(self) -> None:
        """Perform SSL handshake (mock implementation)."""
        self._did_handshake = True

    def getpeercert(self, binary_form: bool = False) -> _PeerCertRetDictType:
        """Get the peer certificate (mock implementation).

        Args:
            binary_form: Whether to return binary form (unused)

        Returns:
            Mock certificate dictionary
        """
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

    def ciper(self) -> tuple[str, str, str]:
        """Get cipher information (mock implementation).

        Returns:
            Tuple of (cipher_name, protocol, key_exchange_algorithm)
        """
        return "ADH", "AES256", "SHA"

    def compression(self) -> Options:
        """Get compression options (mock implementation).

        Returns:
            SSL options constant
        """
        return ssl.OP_NO_COMPRESSION

    def unwrap(self) -> MocketSocket:
        """Unwrap the SSL socket and return the underlying socket.

        Returns:
            The original MocketSocket
        """
        return self._original_socket

    @classmethod
    def _create(
        cls,
        sock: MocketSocket,
        ssl_context: ssl.SSLContext | None = None,
        server_hostname: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> MocketSSLSocket:
        """Create an SSL socket from a regular socket.

        Args:
            sock: Socket to wrap
            ssl_context: SSL context (optional)
            server_hostname: Server hostname
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            New MocketSSLSocket instance
        """
        ssl_socket = MocketSSLSocket()
        ssl_socket._original_socket = sock
        ssl_socket._true_socket = sock._true_socket

        if ssl_context:
            ssl_socket._true_socket = ssl_context.wrap_socket(
                sock=ssl_socket._true_socket,
                server_hostname=server_hostname,
            )

        ssl_socket._kwargs = kwargs

        ssl_socket._timeout = sock._timeout

        ssl_socket._host = sock._host
        ssl_socket._port = sock._port
        ssl_socket._address = sock._address

        ssl_socket._io = sock._io
        ssl_socket._entry = sock._entry

        return ssl_socket
