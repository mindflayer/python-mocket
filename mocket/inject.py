from __future__ import annotations

import contextlib
import socket
import ssl
from types import ModuleType
from typing import Any

import urllib3

_patches_restore: dict[tuple[ModuleType, str], Any] = {}


def _patch(module: ModuleType, name: str, patched_value: Any) -> None:
    with contextlib.suppress(KeyError):
        original_value, module.__dict__[name] = module.__dict__[name], patched_value
        _patches_restore[(module, name)] = original_value


def _restore(module: ModuleType, name: str) -> None:
    if original_value := _patches_restore.pop((module, name)):
        module.__dict__[name] = original_value


def enable() -> None:
    from mocket.socket import (
        MocketSocket,
        mock_create_connection,
        mock_getaddrinfo,
        mock_gethostbyname,
        mock_gethostname,
        mock_inet_pton,
        mock_socketpair,
    )
    from mocket.ssl.context import MocketSSLContext, mock_wrap_socket
    from mocket.urllib3 import (
        mock_match_hostname as mock_urllib3_match_hostname,
    )
    from mocket.urllib3 import (
        mock_ssl_wrap_socket as mock_urllib3_ssl_wrap_socket,
    )

    patches = {
        # stdlib: socket
        (socket, "socket"): MocketSocket,
        (socket, "create_connection"): mock_create_connection,
        (socket, "getaddrinfo"): mock_getaddrinfo,
        (socket, "gethostbyname"): mock_gethostbyname,
        (socket, "gethostname"): mock_gethostname,
        (socket, "inet_pton"): mock_inet_pton,
        (socket, "SocketType"): MocketSocket,
        (socket, "socketpair"): mock_socketpair,
        # stdlib: ssl
        (ssl, "SSLContext"): MocketSSLContext,
        (ssl, "wrap_socket"): mock_wrap_socket,  # python < 3.12.0
        # urllib3
        (urllib3.connection, "match_hostname"): mock_urllib3_match_hostname,
        (urllib3.connection, "ssl_wrap_socket"): mock_urllib3_ssl_wrap_socket,
        (urllib3.util, "ssl_wrap_socket"): mock_urllib3_ssl_wrap_socket,
        (urllib3.util.ssl_, "ssl_wrap_socket"): mock_urllib3_ssl_wrap_socket,
        (urllib3.util.ssl_, "wrap_socket"): mock_urllib3_ssl_wrap_socket,  # urllib3 < 2
    }

    for (module, name), new_value in patches.items():
        _patch(module, name, new_value)

    with contextlib.suppress(ImportError):
        from urllib3.contrib.pyopenssl import extract_from_urllib3

        extract_from_urllib3()


def disable() -> None:
    for module, name in list(_patches_restore.keys()):
        _restore(module, name)

    with contextlib.suppress(ImportError):
        from urllib3.contrib.pyopenssl import inject_into_urllib3

        inject_into_urllib3()
