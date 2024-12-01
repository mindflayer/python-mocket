import io
import os

from typing_extensions import Buffer

from mocket.core.mocket import Mocket
from mocket.core.types import Address


class MocketSocketIO(io.BytesIO):
    def __init__(self, address: Address) -> None:
        self._address = address
        super().__init__()

    def write(self, content: Buffer) -> int:
        bytes_written = super().write(content)

        _, w_fd = Mocket.get_pair(self._address)
        if w_fd:
            return os.write(w_fd, content)

        return bytes_written
