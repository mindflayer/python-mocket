# coding=utf-8
from __future__ import unicode_literals
import functools
import socket
from collections import defaultdict
from io import BytesIO


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
gethostbyname = lambda host: '127.0.0.1'
gethostname = lambda: 'localhost'
getaddrinfo = lambda host, port, family=None, socktype=None, proto=None, flags=None: [(2, 1, 6, '', (host, port))]


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
        self.fd = BytesIO()
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

    def recv(self, buffersize, flags=None):
        return self.fd.readline(buffersize)

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
    _entries = defaultdict(list)
    _requests = []

    @classmethod
    def register(cls, *entries):
        for entry in entries:
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
        cls._entries = defaultdict(list)
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
    request_cls = str
    response_cls = str

    def __init__(self, location, responses):
        self.location = location
        self.responses = responses or (self.response_cls(),)
        self.response_index = 0

    def can_handle(self, data):
        return True

    def collect(self, data):
        req = self.request_cls(data)
        Mocket.collect(req)

    def get_response(self):
        response = self.responses[self.response_index]
        if self.response_index < len(self.responses) - 1:
            self.response_index += 1
        return response.data


class Mocketizer(object):
    def __init__(self, instance):
        self.instance = instance

    def __enter__(self):
        Mocket.enable()
        self.check_and_call('mocketize_setup')

    def __exit__(self, type, value, tb):
        self.check_and_call('mocketize_teardown')
        Mocket.disable()
        Mocket.reset()

    def check_and_call(self, method):
        method = getattr(self.instance, method, None)
        if callable(method):
            method()

    @staticmethod
    def wrap(test):
        @functools.wraps(test)
        def wrapper(*args, **kw):
            with Mocketizer(args[0]):
                return test(*args, **kw)
        return wrapper
mocketize = Mocketizer.wrap
