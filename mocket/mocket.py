from StringIO import StringIO
import socket

__all__ = (
    'true_socket',
    'true_create_connection',
    'true_gethostbyname',
    'true_gethostname',
    'true_getaddrinfo',
    'gethostbyname',
    'gethostname',
    'getaddrinfo',
    'create_connection',
    'MocketSocket',
)

true_socket = socket.socket
true_create_connection = socket.create_connection
true_gethostbyname = socket.gethostbyname
true_gethostname = socket.gethostname
true_getaddrinfo = socket.getaddrinfo
gethostbyname = lambda host: host
gethostname = lambda: 'localhost'
getaddrinfo = lambda host, port, **kwargs: [(2, 1, 6, '', (host, port))]
CRLF = '\r\n'


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, sender_address=None):
    s = MocketSocket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
        s.settimeout(timeout)
    s.connect(address)
    return s


class MocketFile(StringIO):
    def read(self, amount=None):
        return StringIO.read(self, amount or self.len)


class MocketSocket(object):
    def __init__(self, family, type, proto=0):
        self.setsockopt(family, type, proto)
        self.settimeout(socket._GLOBAL_DEFAULT_TIMEOUT)
        self.true_socket = true_socket(family, type, proto)
        self.fd = MocketFile()
        self._closed = True
        self._sock = self

    def setsockopt(self, family, type, protocol):
        self.family = family
        self.protocol = protocol
        self.type = type

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        self._address = (self._host, self._port) = address
        self._closed = False

    def close(self):
        if not self._closed:
            self.true_socket.close()
        self._closed = True

    def makefile(self, mode='r', bufsize=-1):
        self._mode = mode
        self._bufsize = bufsize
        return self.fd

    def sendall(self, data, *args, **kwargs):
        from .registry import Mocket
        entry = Mocket.get_entry(self._host, self._port, data)
        if not entry:
            return self.true_sendall(data, *args, **kwargs)
        entry.collect(data)
        self.fd.seek(0)
        self.fd.write(entry.get_response())
        self.fd.seek(0)

    def true_sendall(self, data, *args, **kwargs):
        self.true_socket.connect(self._address)
        self.true_socket.sendall(data, *args, **kwargs)
        recv = True
        while recv:
            try:
                recv = self.true_socket.recv(16)
                self.true_socket.settimeout(0.0)
                self.fd.write(recv)
            except socket.error:
                break
        self.fd.seek(0)
        self.true_socket.close()
