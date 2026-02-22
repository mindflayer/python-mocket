"""Mocket socket I/O implementation."""

from __future__ import annotations

import io
import os

from mocket.mocket import Mocket


class MocketSocketIO(io.BytesIO):
    """A BytesIO wrapper that integrates with Mocket's pipe-based I/O."""

    def __init__(self, address: tuple) -> None:
        """Initialize the socket I/O with a socket address.

        Args:
            address: Tuple of (host, port)
        """
        self._address = address
        super().__init__()

    def write(self, content: bytes) -> int:
        """Write content to the buffer and the pipe if available.

        Args:
            content: Bytes to write

        Returns:
            Number of bytes written
        """
        super().write(content)

        _, w_fd = Mocket.get_pair(self._address)
        if w_fd:
            os.write(w_fd, content)
        return len(content)
