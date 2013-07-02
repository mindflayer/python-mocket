from StringIO import StringIO
import functools
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
    'Mocket',
    'MocketEntry',
    'mocketize',
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


class MocketSocket(object):
    def __init__(self, family, type, proto=0):
        self.setsockopt(family, type, proto)
        self.settimeout(socket._GLOBAL_DEFAULT_TIMEOUT)
        self.true_socket = true_socket(family, type, proto)
        self.fd = StringIO()
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


class Mocket(object):
    _entries = {}
    _requests = []

    @classmethod
    def register(cls, *entries):
        for entry in entries:
            if entry.location not in cls._entries:
                cls._entries[entry.location] = []
            cls._entries[entry.location].append(entry)

    @classmethod
    def get_entry(cls, host, port, data):
        entries = cls._entries.get((host, port), [])
        for entry in entries:
            if entry.can_handle(data):
                return entry

    @classmethod
    def collect(cls, data):
        cls._requests.append(data)

    @classmethod
    def reset(cls):
        cls._entries = {}
        cls._requests = []

    @classmethod
    def last_request(cls):
        if cls._requests:
            return cls._requests[-1]

    @classmethod
    def remove_last_request(cls):
        if cls._requests:
            del cls._requests[-1]

    @staticmethod
    def enable():
        socket.socket = socket.__dict__['socket'] = MocketSocket
        socket._socketobject = socket.__dict__['_socketobject'] = MocketSocket
        socket.SocketType = socket.__dict__['SocketType'] = MocketSocket
        socket.create_connection = socket.__dict__['create_connection'] = create_connection
        socket.gethostname = socket.__dict__['gethostname'] = gethostname
        socket.gethostbyname = socket.__dict__['gethostbyname'] = gethostbyname
        socket.getaddrinfo = socket.__dict__['getaddrinfo'] = getaddrinfo
        socket.inet_aton = socket.__dict__['inet_aton'] = gethostbyname

    @staticmethod
    def disable():
        socket.socket = socket.__dict__['socket'] = true_socket
        socket._socketobject = socket.__dict__['_socketobject'] = true_socket
        socket.SocketType = socket.__dict__['SocketType'] = true_socket
        socket.create_connection = socket.__dict__['create_connection'] = true_create_connection
        socket.gethostname = socket.__dict__['gethostname'] = true_gethostname
        socket.gethostbyname = socket.__dict__['gethostbyname'] = true_gethostbyname
        socket.getaddrinfo = socket.__dict__['getaddrinfo'] = true_getaddrinfo
        socket.inet_aton = socket.__dict__['inet_aton'] = true_gethostbyname


class MocketEntry(object):
    request_cls = NotImplemented
    response_cls = NotImplemented

    def __init__(self, location, responses):
        self.location = location
        self.responses = responses or (self.response_cls(),)
        self.response_index = 0

    def can_handle(self, data):
        raise NotImplementedError

    def collect(self, data):
        Mocket.collect(self.request_cls(data))

    def get_response(self):
        response = self.responses[self.response_index]
        if self.response_index < len(self.responses) - 1:
            self.response_index += 1
        return str(response)


def mocketize(test):
    @functools.wraps(test)
    def wrapper(*args, **kw):
        Mocket.enable()

        instance = args[0]

        mocketize_setup = getattr(instance, 'mocketize_setup', None)
        if mocketize_setup and callable(mocketize_setup):
            mocketize_setup()

        try:
            return test(*args, **kw)
        finally:
            Mocket.disable()
            Mocket.reset()

            mocketize_teardown = getattr(instance, 'mocketize_teardown', None)
            if mocketize_teardown and callable(mocketize_teardown):
                mocketize_teardown()

    return wrapper
