import socket

import pytest

from mocket import Mocket, MocketEntry, mocketize
from mocket.socket import MocketSocket


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


def test_recvfrom_into():
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    test_data = b"abc123"
    sock._io = type("MockIO", (), {"read": lambda self, n: test_data})()
    buf = bytearray(10)
    nbytes, addr = sock.recvfrom_into(buf)
    assert nbytes == len(test_data)
    assert buf[:nbytes] == test_data
    assert addr == sock._address
