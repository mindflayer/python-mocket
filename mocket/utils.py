import io
import os
import ssl


SSL_PROTOCOL = ssl.PROTOCOL_SSLv23


class MocketSocketCore(io.BytesIO):
    def write(self, content):
        super(MocketSocketCore, self).write(content)

        from mocket import Mocket

        if Mocket.r_fd and Mocket.w_fd:
            os.write(Mocket.w_fd, content)


def wrap_ssl_socket(
    cls,
    sock,
    context,
    keyfile=None,
    certfile=None,
    server_side=False,
    cert_reqs=ssl.CERT_NONE,
    ssl_version=SSL_PROTOCOL,
    ca_certs=None,
    do_handshake_on_connect=True,
    suppress_ragged_eofs=True,
    ciphers=None,
):
    return cls(
        sock=sock,
        keyfile=keyfile,
        certfile=certfile,
        server_side=server_side,
        cert_reqs=cert_reqs,
        ssl_version=ssl_version,
        ca_certs=ca_certs,
        do_handshake_on_connect=do_handshake_on_connect,
        suppress_ragged_eofs=suppress_ragged_eofs,
        ciphers=ciphers,
        _context=context,
    )
