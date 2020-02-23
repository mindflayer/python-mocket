import io
import codecs
import os
import ssl

from mocket.compat import encode_to_bytes, decode_from_bytes


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


def hexdump(binary_string):
    r"""
    >>> hexdump(b"bar foobar foo")
    '62 61 72 20 66 6F 6F 62 61 72 20 66 6F 6F'
    """
    bs = decode_from_bytes(codecs.encode(binary_string, 'hex_codec')).upper()
    return " ".join(a + b for a, b in zip(bs[::2], bs[1::2]))


def hexload(string):
    r"""
    >>> hexload("62 61 72 20 66 6F 6F 62 61 72 20 66 6F 6F")
    b'bar foobar foo'
    """
    string_no_spaces = "".join(string.split())
    return codecs.decode(encode_to_bytes(string_no_spaces), 'hex_codec')
