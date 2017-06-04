import io
import os


class MocketSocketCore(io.BytesIO):
    r_fd = None
    w_fd = None

    def write(self, content):
        super(MocketSocketCore, self).write(content)

        if self.r_fd and self.w_fd:
            os.write(self.w_fd, content)
