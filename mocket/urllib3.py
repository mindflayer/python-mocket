from __future__ import annotations

from typing import Any

import urllib3
from mocket.socket import MocketSocket
from mocket.ssl.context import MocketSSLContext
from mocket.ssl.socket import MocketSSLSocket

true_ssl_wrap_socket = urllib3.util.ssl_.ssl_wrap_socket


def mock_match_hostname(*args: Any) -> None:
    return None


def mock_ssl_wrap_socket(
    sock: MocketSocket,
    *args: Any,
    **kwargs: Any,
) -> MocketSSLSocket:
    context = MocketSSLContext()
    return context.wrap_socket(sock, *args, **kwargs)
