import binascii
import io
import os
import ssl

from .compat import decode_from_bytes, encode_to_bytes

SSL_PROTOCOL = ssl.PROTOCOL_SSLv23


class MocketSocketCore(io.BytesIO):
    def write(self, content):
        super(MocketSocketCore, self).write(content)

        from mocket import Mocket

        if Mocket.r_fd and Mocket.w_fd:
            os.write(Mocket.w_fd, content)


def hexdump(binary_string):
    r"""
    >>> hexdump(b"bar foobar foo") == decode_from_bytes(encode_to_bytes("62 61 72 20 66 6F 6F 62 61 72 20 66 6F 6F"))
    True
    """
    bs = decode_from_bytes(binascii.hexlify(binary_string).upper())
    return " ".join(a + b for a, b in zip(bs[::2], bs[1::2]))


def hexload(string):
    r"""
    >>> hexload("62 61 72 20 66 6F 6F 62 61 72 20 66 6F 6F") == encode_to_bytes("bar foobar foo")
    True
    """
    string_no_spaces = "".join(string.split())
    return encode_to_bytes(binascii.unhexlify(string_no_spaces))


def get_mocketize(wrapper_):
    import decorator

    if decorator.__version__ < "5":  # pragma: no cover
        return decorator.decorator(wrapper_)
    return decorator.decorator(wrapper_, kwsyntax=True)


class MocketMode:
    __shared_state = {}
    STRICT = None

    def __init__(self):
        self.__dict__ = self.__shared_state
