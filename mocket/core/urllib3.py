from __future__ import annotations

from typing import Any

from mocket.core.socket import MocketSocket
from mocket.core.ssl.context import MocketSSLContext
from mocket.core.ssl.socket import MocketSSLSocket


def mock_match_hostname(*args: Any) -> None:
    return None


def mock_ssl_wrap_socket(
    sock: MocketSocket,
    *args: Any,
    **kwargs: Any,
) -> MocketSSLSocket:
    context = MocketSSLContext()
    return context.wrap_socket(sock, *args, **kwargs)
