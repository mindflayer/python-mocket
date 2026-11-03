import asyncio
import socket

import pytest

from mocket import Mocketizer
from mocket.socket import MocketSocket, _loopback_socketpair, mock_socketpair


def test_socketpair_returns_a_real_connected_pair():
    """socketpair() must keep working while Mocket is enabled.

    On Windows there is no C-level socketpair(), and the standard library
    fallback resolves the module-level ``socket`` name, which Mocket has
    swapped for MocketSocket. The pair therefore has to be built from the real
    socket class.
    """
    with Mocketizer():
        a, b = socket.socketpair()
        try:
            a.send(b"ping")
            assert b.recv(4) == b"ping"
            b.send(b"pong")
            assert a.recv(4) == b"pong"
        finally:
            a.close()
            b.close()


def test_asyncio_event_loop_can_be_created():
    """asyncio creates its self-pipe with socketpair() when a loop is built."""
    with Mocketizer():
        loop = asyncio.new_event_loop()
        try:
            assert loop is not None
        finally:
            loop.close()


def test_socketpair_does_not_disable_the_mock_layer():
    """The loopback pair must not leak past socketpair() into user sockets."""
    with Mocketizer():
        a, b = socket.socketpair()
        a.close()
        b.close()

        assert socket.socket is MocketSocket
        assert not isinstance(a, MocketSocket)


def test_mock_socketpair_without_the_c_function(monkeypatch):
    """Force the pure-Python path so POSIX CI covers it too."""
    import _socket

    monkeypatch.delattr(_socket, "socketpair", raising=False)

    with Mocketizer():
        a, b = socket.socketpair()
        try:
            a.send(b"ping")
            assert b.recv(4) == b"ping"
        finally:
            a.close()
            b.close()

        loop = asyncio.new_event_loop()
        loop.close()


def test_loopback_socketpair_rejects_a_foreign_peer(monkeypatch):
    """CVE-2024-3219: the listener is reachable, so the peer must be ours.

    The hijack has to be installed on ``mocket.socket.true_socket``, which is
    the name ``_loopback_socketpair`` resolves. Patching ``socket.socket``
    instead only works while that name still points at the same class: the
    gevent tests in this suite call ``monkey.patch_socket()`` at import time,
    which leaves ``socket.socket`` bound to gevent's subclass while
    ``true_socket`` keeps the original one, so the hijack silently missed.
    """
    from mocket import socket as mocket_socket_module
    from mocket.socket import _loopback_socketpair

    real = mocket_socket_module.true_socket
    listener = real(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    attacker = real(socket.AF_INET, socket.SOCK_STREAM)
    attacker.connect(listener.getsockname())
    hijacked, foreign_peer = listener.accept()
    hijacked_fd = hijacked.detach()

    class HijackedListener(real):
        def _accept(self):
            # _loopback_socketpair() connects with setblocking(False), exactly
            # like CPython's own fallback, and relies on accept() to wait for
            # the handshake before the peer check calls getpeername(). Linux
            # leaves that connect in SYN_SENT for a moment, so skipping the
            # wait here makes getpeername() raise ENOTCONN instead of the
            # ConnectionError this test is about. Drain the real connection
            # first; its peer is nobody we care about.
            # Socket._accept() is CPython-internal and missing from the type
            # stubs, hence the ignore: it is the only way to bypass the
            # override above without recursing through accept().
            real_fd, _ = real._accept(self)  # type: ignore[attr-defined]
            # Wrap it before closing: on Windows a socket descriptor is not
            # an OS file descriptor, so os.close() would raise EBADF.
            real(fileno=real_fd).close()
            return hijacked_fd, foreign_peer

    monkeypatch.setattr(mocket_socket_module, "true_socket", HijackedListener)
    try:
        with pytest.raises(ConnectionError, match="Unexpected peer connection"):
            _loopback_socketpair()
    finally:
        listener.close()
        attacker.close()


def test_mock_socketpair_prefers_the_c_implementation(monkeypatch):
    """When the interpreter has _socket.socketpair() there is nothing to build."""
    import _socket

    sentinel = (object(), object())
    monkeypatch.setattr(
        _socket, "socketpair", lambda *args, **kwargs: sentinel, raising=False
    )

    assert mock_socketpair() is sentinel


def test_loopback_socketpair_works_over_ipv6():
    """AF_INET6 is served from ::1; the pair must be just as usable as IPv4."""
    probe = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        probe.bind(("::1", 0))
    except OSError:
        pytest.skip("IPv6 loopback is not available")
    finally:
        probe.close()

    a, b = _loopback_socketpair(socket.AF_INET6)
    try:
        a.send(b"ping")
        assert b.recv(4) == b"ping"
    finally:
        a.close()
        b.close()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"family": socket.AF_UNSPEC}, "Only AF_INET and AF_INET6 address families"),
        ({"socktype": socket.SOCK_DGRAM}, "Only SOCK_STREAM socket type"),
        ({"proto": 6}, "Only protocol zero"),
    ],
)
def test_loopback_socketpair_rejects_unsupported_options(kwargs, message):
    """Whatever the loopback fallback cannot honour is refused before binding."""
    with pytest.raises(ValueError, match=message):
        _loopback_socketpair(**kwargs)


def test_loopback_socketpair_closes_the_client_when_accept_fails(monkeypatch):
    """A failing accept() must not leak the socket that already connected."""
    from mocket import socket as mocket_socket_module

    real = mocket_socket_module.true_socket
    created = []

    class FailingListener(real):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

        def _accept(self):
            raise OSError("accept() failed")

    monkeypatch.setattr(mocket_socket_module, "true_socket", FailingListener)
    with pytest.raises(OSError, match="accept"):
        _loopback_socketpair()

    _listener, client = created
    assert client.fileno() == -1


def test_loopback_socketpair_closes_both_sockets_on_a_peer_mismatch(monkeypatch):
    """CVE-2024-3219: when the peer is not ours, both halves are closed."""
    from mocket import socket as mocket_socket_module

    real = mocket_socket_module.true_socket
    created = []

    class DoctoredPeers(real):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

        def getpeername(self):
            host, port = super().getpeername()
            return host, port + 1

    monkeypatch.setattr(mocket_socket_module, "true_socket", DoctoredPeers)
    with pytest.raises(ConnectionError, match="Unexpected peer connection"):
        _loopback_socketpair()

    _listener, client, accepted = created
    assert client.fileno() == -1
    assert accepted.fileno() == -1
