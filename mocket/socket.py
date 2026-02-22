"""Mock socket implementation for Mocket."""

from __future__ import annotations

import contextlib
import errno
import os
import select
import socket
from types import TracebackType
from typing import Any, Type

from typing_extensions import Self

from mocket.entry import MocketEntry
from mocket.io import MocketSocketIO
from mocket.mocket import Mocket
from mocket.mode import MocketMode
from mocket.types import (
    Address,
    ReadableBuffer,
    WriteableBuffer,
    _RetAddress,
)

true_gethostbyname = socket.gethostbyname
true_socket = socket.socket


def mock_create_connection(
    address: Address,
    timeout: float | None = None,
    source_address: Address | None = None,
) -> socket.socket:
    """Create a mock socket connection.

    Args:
        address: (host, port) tuple
        timeout: Connection timeout in seconds
        source_address: Source address for binding (unused)

    Returns:
        MocketSocket instance
    """
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
    """Mock socket.getaddrinfo function.

    Args:
        host: Hostname
        port: Port number
        family: Address family (ignored)
        type: Socket type (ignored)
        proto: Protocol (ignored)
        flags: Flags (ignored)

    Returns:
        List of address info tuples
    """
    return [(2, 1, 6, "", (host, port))]


def mock_gethostbyname(hostname: str) -> str:
    """Mock socket.gethostbyname function.

    Args:
        hostname: Hostname to resolve (unused)

    Returns:
        Localhost IP address
    """
    return "127.0.0.1"


def mock_gethostname() -> str:
    """Mock socket.gethostname function.

    Returns:
        Localhost hostname
    """
    return "localhost"


def mock_inet_pton(address_family: int, ip_string: str) -> bytes:
    """Mock socket.inet_pton function.

    Args:
        address_family: Address family (unused)
        ip_string: IP string (unused)

    Returns:
        Localhost as bytes
    """
    return bytes("\x7f\x00\x00\x01", "utf-8")


def mock_socketpair(
    *args: Any,
    **kwargs: Any,
) -> tuple[socket.socket, socket.socket]:
    """Mock socket.socketpair function.

    Returns a real socketpair() used by asyncio loop for supporting
    calls made by fastapi and similar services.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of two connected sockets
    """
    import _socket

    return _socket.socketpair(*args, **kwargs)


class MocketSocket:
    """Mock socket implementation for Mocket."""

    def __init__(
        self,
        family: socket.AddressFamily | int = socket.AF_INET,
        type: socket.SocketKind | int = socket.SOCK_STREAM,
        proto: int = 0,
        fileno: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a Mocket socket.

        Args:
            family: Address family
            type: Socket type
            proto: Protocol number
            fileno: File descriptor (unused)
            **kwargs: Additional keyword arguments
        """
        self._family = family
        self._type = type
        self._proto = proto

        self._kwargs = kwargs
        self._true_socket = true_socket(family, type, proto)

        self._buflen = 65536
        self._timeout: float | None = None

        self._host = None
        self._port = None
        self._address = None

        self._io = None
        self._entry = None

    def __str__(self) -> str:
        """Return a string representation of the socket."""
        return f"({self.__class__.__name__})(family={self.family} type={self.type} protocol={self.proto})"

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        type_: Type[BaseException] | None,  # noqa: UP006
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit context manager and close socket."""
        self.close()

    @property
    def family(self) -> int:
        """Get the address family."""
        return self._family

    @property
    def type(self) -> int:
        """Get the socket type."""
        return self._type

    @property
    def proto(self) -> int:
        """Get the protocol number."""
        return self._proto

    @property
    def io(self) -> MocketSocketIO:
        """Get or create the socket I/O object."""
        if self._io is None:
            self._io = MocketSocketIO((self._host, self._port))
        return self._io

    def fileno(self) -> int:
        """Get the file descriptor for reading.

        Returns:
            File descriptor number
        """
        address = (self._host, self._port)
        r_fd, _ = Mocket.get_pair(address)
        if not r_fd:
            r_fd, w_fd = os.pipe()
            Mocket.set_pair(address, (r_fd, w_fd))
        return r_fd

    def gettimeout(self) -> float | None:
        """Get the socket timeout.

        Returns:
            Timeout in seconds or None
        """
        return self._timeout

    def setsockopt(self, family: int, type: int, proto: int) -> None:
        """Set socket options.

        Args:
            family: Address family
            type: Socket type
            proto: Protocol number
        """
        self._family = family
        self._type = type
        self._proto = proto

        if self._true_socket:
            self._true_socket.setsockopt(family, type, proto)

    def settimeout(self, timeout: float | None) -> None:
        """Set the socket timeout.

        Args:
            timeout: Timeout in seconds or None
        """
        self._timeout = timeout

    @staticmethod
    def getsockopt(level: int, optname: int, buflen: int | None = None) -> int:
        """Get socket option (mock implementation).

        Args:
            level: Socket option level
            optname: Socket option name
            buflen: Buffer length (unused)

        Returns:
            SOCK_STREAM constant
        """
        return socket.SOCK_STREAM

    def getpeername(self) -> _RetAddress:
        """Get the remote socket address.

        Returns:
            Address of the remote socket
        """
        return self._address

    def setblocking(self, block: bool) -> None:
        """Set the socket to blocking or non-blocking mode.

        Args:
            block: True for blocking, False for non-blocking
        """
        self.settimeout(None) if block else self.settimeout(0.0)

    def getblocking(self) -> bool:
        """Check if the socket is in blocking mode.

        Returns:
            True if blocking, False otherwise
        """
        return self.gettimeout() is None

    def getsockname(self) -> _RetAddress:
        """Get the local socket address.

        Returns:
            Local socket address
        """
        return socket.gethostbyname(self._address[0]), self._address[1]

    def connect(self, address: Address) -> None:
        """Connect the socket to a remote address.

        Args:
            address: (host, port) tuple
        """
        self._address = self._host, self._port = address
        Mocket._address = address

    def makefile(self, mode: str = "r", bufsize: int = -1) -> MocketSocketIO:
        """Create a file object for the socket.

        Args:
            mode: Mode string (unused)
            bufsize: Buffer size (unused)

        Returns:
            MocketSocketIO object
        """
        return self.io

    def get_entry(self, data: bytes) -> MocketEntry | None:
        """Get a matching entry for the given data.

        Args:
            data: Request data

        Returns:
            Matching MocketEntry or None
        """
        return Mocket.get_entry(self._host, self._port, data)

    def sendto(
        self,
        data: ReadableBuffer,
        address: Address | None = None,
    ) -> int:
        """Send data to a specific address (UDP-like).

        Args:
            data: Data to send
            address: Destination address

        Returns:
            Number of bytes sent
        """
        self.connect(address)
        self.sendall(data)
        return len(data)

    def sendall(
        self,
        data: ReadableBuffer,
        entry: MocketEntry | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Send all data through the socket.

        Args:
            data: Data to send
            entry: Pre-matched entry (optional)
            *args: Additional arguments
            **kwargs: Additional keyword arguments
        """
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

    def sendmsg(
        self,
        buffers: list[ReadableBuffer],
        ancdata: list[tuple[int, bytes]] | None = None,
        flags: int = 0,
        address: Address | None = None,
    ) -> int:
        """Send a message through multiple buffers.

        Args:
            buffers: List of buffers to send
            ancdata: Ancillary data (unused)
            flags: Flags (unused)
            address: Destination address (unused)

        Returns:
            Number of bytes sent
        """
        if not buffers:
            return 0

        data = b"".join(bytes(b) for b in buffers)
        self.sendall(data)
        return len(data)

    def recvmsg(
        self,
        buffersize: int | None = None,
        ancbufsize: int | None = None,
        flags: int = 0,
    ) -> tuple[bytes, list[tuple[int, bytes]]]:
        """Receive a message from the socket.

        This is a mock implementation that reads from the MocketSocketIO.

        Args:
            buffersize: Size of buffer to receive
            ancbufsize: Ancillary buffer size (unused)
            flags: Flags (unused)

        Returns:
            Tuple of (data, ancillary_data)
        """
        try:
            data = self.recv(buffersize)
        except BlockingIOError:
            return b"", []

        return data, []

    def recvmsg_into(
        self,
        buffers: list[ReadableBuffer],
        ancbufsize: int | None = None,
        flags: int = 0,
        address: Address | None = None,
    ) -> int:
        """Receive a message into multiple buffers.

        This is a mock implementation that reads from the MocketSocketIO.

        Args:
            buffers: List of buffers to receive into
            ancbufsize: Ancillary buffer size (unused)
            flags: Flags (unused)
            address: Address (unused)

        Returns:
            Number of bytes received
        """
        if not buffers:
            return 0

        try:
            data = self.recv(len(buffers[0]))
        except BlockingIOError:
            return 0

        for i, buffer in enumerate(buffers):
            if i < len(data):
                buffer[: len(data)] = data
            else:
                buffer[:] = b""
        return len(data)

    def recvfrom_into(
        self,
        buffer: WriteableBuffer,
        buffersize: int | None = None,
        flags: int | None = None,
    ) -> tuple[int, _RetAddress]:
        """Receive data into a buffer and return the source address.

        Args:
            buffer: Buffer to receive into
            buffersize: Size to receive
            flags: Flags (unused)

        Returns:
            Tuple of (bytes_received, source_address)
        """
        return self.recv_into(buffer, buffersize, flags), self._address

    def recv_into(
        self,
        buffer: WriteableBuffer,
        buffersize: int | None = None,
        flags: int | None = None,
    ) -> int:
        """Receive data into a buffer.

        Args:
            buffer: Buffer to receive into
            buffersize: Number of bytes to receive
            flags: Flags (unused)

        Returns:
            Number of bytes received
        """
        if hasattr(buffer, "write"):
            return buffer.write(self.recv(buffersize))

        if buffersize is None:
            buffersize = len(buffer)

        data = self.recv(buffersize)
        if data:
            buffer[: len(data)] = data
        return len(data)

    def recvfrom(
        self, buffersize: int, flags: int | None = None
    ) -> tuple[bytes, _RetAddress]:
        """Receive data and the source address.

        Args:
            buffersize: Number of bytes to receive
            flags: Flags (unused)

        Returns:
            Tuple of (data, source_address)
        """
        return self.recv(buffersize, flags), self._address

    def recv(self, buffersize: int, flags: int | None = None) -> bytes:
        """Receive data from the socket.

        Args:
            buffersize: Maximum number of bytes to receive
            flags: Flags (unused)

        Returns:
            Received bytes

        Raises:
            BlockingIOError: If socket is non-blocking and no data available
        """
        r_fd, _ = Mocket.get_pair((self._host, self._port))
        if r_fd:
            return os.read(r_fd, buffersize)
        data = self.io.read(buffersize)
        if data:
            return data
        # used by Redis mock
        exc = BlockingIOError()
        exc.errno = errno.EWOULDBLOCK
        exc.args = (0,)
        raise exc

    def true_sendall(self, data: bytes, *args: Any, **kwargs: Any) -> bytes:
        """Send data through the real socket and receive response.

        Args:
            data: Data to send
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response bytes from the real socket

        Raises:
            StrictMocketException: If operation not allowed in STRICT mode
        """
        if not MocketMode.is_allowed(self._address):
            MocketMode.raise_not_allowed(self._address, data)

        # try to get the response from recordings
        if Mocket._record_storage:
            record = Mocket._record_storage.get_record(
                address=self._address,
                request=data,
            )
            if record is not None:
                return record.response

        host, port = self._address
        host = true_gethostbyname(host)

        with contextlib.suppress(OSError, ValueError):
            # already connected
            self._true_socket.connect((host, port))

        self._true_socket.sendall(data, *args, **kwargs)
        response = b""
        # https://github.com/kennethreitz/requests/blob/master/tests/testserver/server.py#L12
        while True:
            more_to_read = select.select([self._true_socket], [], [], 0.1)[0]
            if not more_to_read and response:
                break
            new_content = self._true_socket.recv(self._buflen)
            if not new_content:
                break
            response += new_content

        # store request+response in recordings
        if Mocket._record_storage:
            Mocket._record_storage.put_record(
                address=self._address,
                request=data,
                response=response,
            )

        return response

    def send(
        self,
        data: ReadableBuffer,
        *args: Any,
        **kwargs: Any,
    ) -> int:
        """Send data through the socket.

        Args:
            data: Data to send
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Number of bytes sent
        """
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

    def accept(self) -> tuple[MocketSocket, _RetAddress]:
        """Accept a connection and return a new MocketSocket object.

        Returns:
            Tuple of (new_socket, client_address)
        """
        new_socket = MocketSocket(
            family=self._family,
            type=self._type,
            proto=self._proto,
        )
        new_socket._address = (self._host, self._port)
        new_socket._host = self._host
        new_socket._port = self._port
        return new_socket, (self._host, self._port)

    def close(self) -> None:
        """Close the socket and underlying true socket."""
        if self._true_socket and not self._true_socket._closed:
            self._true_socket.close()

    def __getattr__(self, name: str) -> Any:
        """Do-nothing catchall function for methods like shutdown().

        Args:
            name: Method name

        Returns:
            A callable that does nothing
        """

        def do_nothing(*args: Any, **kwargs: Any) -> Any:
            pass

        return do_nothing
