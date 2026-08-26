import os
import socket
import ssl
import struct
from unittest.mock import MagicMock

import pytest

from mocket import Mocket, MocketEntry, Mocketizer, mocketize
from mocket.mockhttp import Entry
from mocket.socket import MocketSocket
from mocket.ssl.context import MocketSSLContext, mock_wrap_socket
from mocket.ssl.socket import MocketSSLSocket
from mocket.urllib3 import mock_match_hostname


@pytest.mark.parametrize("blocking", (False, True))
def test_blocking_socket(blocking):
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("locahost", 1234))
    sock.setblocking(blocking)
    assert sock.getblocking() is blocking


@mocketize
def test_udp_socket():
    host = "127.0.0.1"
    port = 9999
    request_data = b"ping"
    response_data = b"pong"

    Mocket.register(MocketEntry((host, port), [response_data]))

    # Your UDP client code
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(request_data, (host, port))
    data, address = sock.recvfrom(1024)

    assert data == response_data
    assert address == (host, port)


def test_recvmsg():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    test_data = b"hello world"
    sock._io = type("MockIO", (), {"read": lambda self, n: test_data})()
    data, ancdata = sock.recvmsg(1024)
    assert data == test_data
    assert ancdata == []


def test_recvmsg_into():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    test_data = b"foobar"
    sock._io = type("MockIO", (), {"read": lambda self, n: test_data})()
    buf = bytearray(10)
    buf2 = bytearray(10)
    buffers = [buf, buf2]
    nbytes = sock.recvmsg_into(buffers)
    assert nbytes == len(test_data)
    assert buf[: len(test_data)] == test_data


def test_recvmsg_into_empty_buffers():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.recvmsg_into([])
    assert result == 0


def test_accept():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    sock._host = "127.0.0.1"
    sock._port = 8080
    new_sock, addr = sock.accept()
    assert isinstance(new_sock, MocketSocket)
    assert new_sock is not sock
    assert addr == ("127.0.0.1", 8080)
    assert new_sock._host == "127.0.0.1"
    assert new_sock._port == 8080


@mocketize
def test_sendmsg():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    sock._host = "127.0.0.1"
    sock._port = 8080
    response_data = b"pong"

    Mocket.register(MocketEntry((sock._host, sock._port), [response_data]))

    msg = [b"foo", b"bar", b"foobaz"]
    total_sent = sock.sendmsg(msg)
    assert total_sent == sum(len(m) for m in msg)
    assert Mocket.last_request() == b"".join(msg)


def test_sendmsg_empty_buffers():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.sendmsg([])
    assert result == 0


def test_recvmsg_no_data():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    # Mock _io.read to return empty bytes
    sock._io = type("MockIO", (), {"read": lambda self, n: b""})()
    data, ancdata = sock.recvmsg(1024)
    assert data == b""
    assert ancdata == []


def test_recvmsg_into_no_data():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    # Mock _io.read to return empty bytes
    sock._io = type("MockIO", (), {"read": lambda self, n: b""})()
    buf = bytearray(10)
    nbytes = sock.recvmsg_into([buf])
    assert nbytes == 0
    assert buf == bytearray(10)


def test_getsockopt():
    # getsockopt is a static method, so we can call it directly
    result = MocketSocket.getsockopt(0, 0)
    assert result == socket.SOCK_STREAM


@pytest.mark.parametrize(
    ("server_hostname", "expected_host"),
    [
        (b"httpbin.local", "httpbin.local"),
        ("httpbin.local", "httpbin.local"),
        (None, "httpbin.local"),
        ("", ""),
        (b"mocket-\xff.local", "mocket-�.local"),
    ],
)
def test_wrap_bio_uses_current_mocket_address(
    monkeypatch, server_hostname, expected_host
):
    monkeypatch.setattr(Mocket, "_address", ("httpbin.local", 443))
    ssl_obj = MocketSSLContext().wrap_bio(
        incoming=None,
        outgoing=None,
        server_hostname=server_hostname,
    )

    assert ssl_obj._host == expected_host
    assert ssl_obj._port == 443
    assert ssl_obj._address == (expected_host, 443)


def test_wrap_bio_preserves_empty_server_hostname_on_getpeercert(monkeypatch):
    monkeypatch.setattr(Mocket, "_address", ("httpbin.local", 443))
    ssl_obj = MocketSSLContext().wrap_bio(
        incoming=None,
        outgoing=None,
        server_hostname="",
    )

    ssl_obj.getpeercert()

    assert ssl_obj._host == ""
    assert ssl_obj._address == ("", 443)


def test_wrap_bio_with_invalid_mocket_address(monkeypatch):
    monkeypatch.setattr(Mocket, "_address", "invalid-address")
    ssl_obj = MocketSSLContext().wrap_bio(
        incoming=None,
        outgoing=None,
        server_hostname=None,
    )

    assert ssl_obj._host is None
    assert ssl_obj._port is None


def test_mock_wrap_socket_delegates_to_context(monkeypatch):
    expected = MocketSSLSocket()

    def fake_wrap_socket(self, sock, *args, **kwargs):
        return expected

    monkeypatch.setattr(MocketSSLContext, "wrap_socket", fake_wrap_socket)

    assert mock_wrap_socket(MocketSocket()) is expected


def test_mock_match_hostname_returns_none():
    assert mock_match_hostname("example.org", object()) is None


def test_getpeercert_does_not_overwrite_empty_host_when_port_missing(monkeypatch):
    monkeypatch.setattr(Mocket, "_address", ("httpbin.local", 443))
    ssl_obj = MocketSSLSocket()
    ssl_obj._host = ""
    ssl_obj._port = None
    ssl_obj._address = ("", None)

    ssl_obj.getpeercert()

    assert ssl_obj._host == ""
    assert ssl_obj._port == 443
    assert ssl_obj._address == ("", 443)


def test_recvfrom_into():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    test_data = b"abc123"
    sock._io = type("MockIO", (), {"read": lambda self, n: test_data})()
    buf = bytearray(10)
    nbytes, addr = sock.recvfrom_into(buf)
    assert nbytes == len(test_data)
    assert buf[:nbytes] == test_data
    assert addr == sock._address


def test_setsockopt_without_optlen():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    sock._true_socket = MagicMock()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock._true_socket.setsockopt.assert_called_once_with(
        socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
    )


def test_setsockopt_with_optlen():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    sock._true_socket = MagicMock()
    linger_value = struct.pack("ii", 1, 5)
    sock.setsockopt(
        socket.SOL_SOCKET, socket.SO_LINGER, linger_value, len(linger_value)
    )
    sock._true_socket.setsockopt.assert_called_once_with(
        socket.SOL_SOCKET, socket.SO_LINGER, linger_value, len(linger_value)
    )


def test_ssl_read_empty_after_handshake_returns_empty_bytes():
    """After handshake, empty SSL reads should not raise SSLWantReadError."""
    sock = MocketSSLSocket()
    sock._io = type("MockIO", (), {"read": lambda self, n: b""})()
    sock._did_handshake = True
    sock._has_written = True

    assert sock.read(1024) == b""


def test_ssl_read_empty_after_handshake_before_write_raises_want_read():
    """After handshake but before writes, empty reads should signal WANT_READ."""
    sock = MocketSSLSocket()
    sock._io = type("MockIO", (), {"read": lambda self, n: b""})()
    sock._did_handshake = True
    sock._has_written = False

    with pytest.raises(ssl.SSLWantReadError):
        sock.read(1024)


def test_ssl_ciper_returns_mock_tuple():
    """Exercise the SSL mock cipher tuple branch for coverage."""
    sock = MocketSSLSocket()
    assert sock.ciper() == ("ADH", "AES256", "SHA")


def test_ssl_getpeercert_uses_mocket_address_when_unset(monkeypatch):
    """Cover getpeercert fallback when host/port are not yet assigned."""
    monkeypatch.setattr(Mocket, "_address", ("example.local", 443))
    sock = MocketSSLSocket()

    cert = sock.getpeercert()

    assert sock._host == "example.local"
    assert sock._port == 443
    assert sock._address == ("example.local", 443)
    assert cert["subjectAltName"][1] == ("DNS", "example.local")


# ---------------------------------------------------------------------------
# New pipe-mechanism tests added to maintain coverage after the large-response
# deadlock fix.
# ---------------------------------------------------------------------------


def test_mocket_shared_io_same_address():
    """Two MocketSocket instances for the same address share one I/O buffer."""
    addr = ("localhost", 9001)
    with Mocketizer():
        s1 = MocketSocket()
        s1.connect(addr)
        s2 = MocketSocket()
        s2.connect(addr)
        # Accessing .io lazily creates and registers the shared buffer
        assert s1.io is s2.io


def test_mocket_shared_io_recreated_after_close():
    """If the shared buffer is closed, accessing .io creates a fresh one."""
    addr = ("localhost", 9002)
    with Mocketizer():
        s = MocketSocket()
        s.connect(addr)
        old_io = s.io
        old_io.close()
        # Force re-evaluation by clearing the cached reference
        s._io = None
        new_io = s.io
        assert not new_io.closed
        assert new_io is not old_io


def test_mocket_pipe_uses_data_false_for_large_response():
    """Responses larger than _buflen use readiness-only signaling, not data in pipe."""
    addr = ("localhost", 9003)
    large_body = "x" * 70_000
    Entry.single_register(
        method=Entry.GET,
        uri="http://localhost:9003/",
        body=large_body,
    )
    with Mocketizer():
        s = MocketSocket()
        s.connect(addr)
        request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        s.sendall(request)
        assert not Mocket.pipe_uses_data(addr), (
            "large response must use readiness-only pipe"
        )


@mocketize
def test_large_response_recv_drains_readiness_sentinel():
    """recv() for a large response drains readiness bytes and re-syncs the pipe.

    This exercises the _sync_readable_pipe() re-sync call (socket.py line 638)
    that runs after draining sentinel bytes from a readiness-only pipe.
    """
    addr = ("localhost", 9004)
    large_body = "y" * 70_000
    Entry.single_register(
        method=Entry.GET,
        uri="http://localhost:9004/",
        body=large_body,
    )
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(addr)
    # Calling fileno() forces pipe creation so the readiness path is active.
    s.fileno()
    s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")

    # The response is large → pipe_uses_data=False → readiness sentinels are used.
    # Collecting the full body exercises the drain + re-sync branch on line 638.
    received = b""
    while True:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            received += chunk
        except BlockingIOError:
            break
    s.close()
    assert large_body.encode() in received


def test_mocket_get_set_io():
    """Mocket.get_io / set_io round-trip."""
    from mocket.io import MocketSocketIO

    addr = ("localhost", 9005)
    buf = MocketSocketIO(addr)
    Mocket.set_io(addr, buf)
    assert Mocket.get_io(addr) is buf


def test_mocket_pipe_uses_data_flag():
    """Mocket.pipe_uses_data / set_pipe_uses_data round-trip."""
    addr = ("localhost", 9006)
    assert not Mocket.pipe_uses_data(addr)
    Mocket.set_pipe_uses_data(addr, True)
    assert Mocket.pipe_uses_data(addr)
    Mocket.set_pipe_uses_data(addr, False)
    assert not Mocket.pipe_uses_data(addr)


def test_mocket_reset_clears_shared_ios():
    """Mocket.reset() clears the shared I/O buffer registry."""
    from mocket.io import MocketSocketIO

    addr = ("localhost", 9007)
    Mocket.set_io(addr, MocketSocketIO(addr))
    Mocket.reset()
    assert Mocket.get_io(addr) is None


def test_mirror_buffer_to_pipe_writes_data():
    """_mirror_buffer_to_pipe writes the unread buffer content into the pipe."""
    addr = ("localhost", 9008)
    s = MocketSocket()
    s.connect(addr)

    # Simulate a small response already buffered (no sendall needed)
    response = b"hello pipe"
    s.io.seek(0)
    s.io.write(response)
    s.io.seek(0)

    # Create the pipe manually
    r_fd, w_fd = os.pipe()
    os.set_blocking(r_fd, False)
    os.set_blocking(w_fd, False)
    Mocket.set_pair(addr, (r_fd, w_fd))

    s._mirror_buffer_to_pipe()
    pipe_bytes = os.read(r_fd, 64)
    os.close(r_fd)
    os.close(w_fd)
    Mocket._socket_pairs.pop(addr, None)

    assert pipe_bytes == response
