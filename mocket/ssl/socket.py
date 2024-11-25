from __future__ import annotations

import ssl
from datetime import datetime, timedelta
from typing import Any

from mocket.compat import encode_to_bytes
from mocket.mocket import Mocket
from mocket.socket import MocketSocket
from mocket.types import _PeerCertRetDictType


class MocketSSLSocket(MocketSocket):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._did_handshake = False
        self._sent_non_empty_bytes = False
        self._original_socket: MocketSocket = self

    def read(self, buffersize: int | None = None) -> bytes:
        rv = self.io.read(buffersize)
        if rv:
            self._sent_non_empty_bytes = True
        if self._did_handshake and not self._sent_non_empty_bytes:
            raise ssl.SSLWantReadError("The operation did not complete (read)")
        return rv

    def write(self, data: bytes) -> int | None:
        return self.send(encode_to_bytes(data))

    def do_handshake(self) -> None:
        self._did_handshake = True

    def getpeercert(self, binary_form: bool = False) -> _PeerCertRetDictType:
        if not (self._host and self._port):
            self._address = self._host, self._port = Mocket._address

        now = datetime.now()
        shift = now + timedelta(days=30 * 12)
        return {
            "notAfter": shift.strftime("%b %d %H:%M:%S GMT"),
            "subjectAltName": (
                ("DNS", f"*.{self._host}"),
                ("DNS", self._host),
                ("DNS", "*"),
            ),
            "subject": (
                (("organizationName", f"*.{self._host}"),),
                (("organizationalUnitName", "Domain Control Validated"),),
                (("commonName", f"*.{self._host}"),),
            ),
        }

    def ciper(self) -> tuple[str, str, str]:
        return ("ADH", "AES256", "SHA")

    def compression(self) -> str | None:
        return ssl.OP_NO_COMPRESSION

    def unwrap(self) -> MocketSocket:
        return self._original_socket
