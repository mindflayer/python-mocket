import asyncio
import socket

import pytest

from mocket import Mocketizer
from mocket.socket import MocketSocket


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
    """CVE-2024-3219: the listener is reachable, so the peer must be ours."""
    from mocket.socket import _loopback_socketpair

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    attacker = socket.socket()
    attacker.connect(listener.getsockname())
    hijacked, _ = listener.accept()
    foreign_peer = hijacked.getpeername()
    hijacked_fd = hijacked.detach()

    def fake_accept(self):
        return hijacked_fd, foreign_peer

    monkeypatch.setattr(socket.socket, "_accept", fake_accept)
    try:
        with pytest.raises(ConnectionError, match="Unexpected peer connection"):
            _loopback_socketpair()
    finally:
        listener.close()
        attacker.close()
