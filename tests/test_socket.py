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
