import io
import os


class MocketSocketCore(io.BytesIO):
    def __init__(self, address) -> None:
        self._address = address
        super().__init__()

    def write(self, content):
        from mocket import Mocket

        super().write(content)

        _, w_fd = Mocket.get_pair(self._address)
        if w_fd:
            os.write(w_fd, content)
