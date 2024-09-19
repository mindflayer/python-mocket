import socket

import pytest

from mocket.mocket import MocketSocket


@pytest.mark.parametrize("blocking", (False, True))
def test_blocking_socket(blocking):
    sock = MocketSocket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("locahost", 1234))
    sock.setblocking(blocking)
    assert sock.getblocking() is blocking
