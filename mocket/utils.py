import binascii
import io
import os
import ssl
from typing import Tuple, Union

from .compat import decode_from_bytes, encode_to_bytes
from .exceptions import StrictMocketException

SSL_PROTOCOL = ssl.PROTOCOL_TLSv1_2


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
    STRICT_ALLOWED = None

    def __init__(self):
        self.__dict__ = self.__shared_state

    def is_allowed(self, location: Union[str, Tuple[str, int]]) -> bool:
        """
        Checks if (`host`, `port`) or at least `host`
        are allowed locations to perform real `socket` calls
        """
        if not self.STRICT:
            return True
        try:
            host, _ = location
        except ValueError:
            host = None
        return location in self.STRICT_ALLOWED or (
            host is not None and host in self.STRICT_ALLOWED
        )

    @staticmethod
    def raise_not_allowed():
        from .mocket import Mocket

        current_entries = [
            (location, "\n    ".join(map(str, entries)))
            for location, entries in Mocket._entries.items()
        ]
        formatted_entries = "\n".join(
            [f"  {location}:\n    {entries}" for location, entries in current_entries]
        )
        raise StrictMocketException(
            "Mocket tried to use the real `socket` module while STRICT mode was active.\n"
            f"Registered entries:\n{formatted_entries}"
        )
