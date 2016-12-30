# coding=utf-8
from __future__ import unicode_literals
from datetime import datetime, timedelta
import socket
import ssl
import collections
from io import BytesIO

import decorator

from .compat import encode_utf8, basestring, byte_type, text_type

__all__ = (
    'true_socket',
    'true_create_connection',
    'true_gethostbyname',
    'true_gethostname',
    'true_getaddrinfo',
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
true_ssl_wrap_socket = ssl.wrap_socket
true_ssl_socket = ssl.SSLSocket
try:
    true_ssl_context = ssl.SSLContext
except AttributeError:
    # Python 2.6
    true_ssl_context = None


class SuperFakeSSLContext(object):
    """ For Python 3.6 """
    class FakeSetter(int):
        def __set__(self, *args):
            pass
    options = FakeSetter()
    verify_mode = FakeSetter(ssl.CERT_OPTIONAL)


class FakeSSLContext(SuperFakeSSLContext):
    def __init__(self, sock=None, server_hostname=None, *args, **kwargs):
        if isinstance(sock, MocketSocket):
            self.sock = sock
            self.sock._host = server_hostname

    @staticmethod
    def load_default_certs(*args, **kwargs):
        pass

    @staticmethod
    def wrap_socket(sock, *args, **kwargs):
        return sock

    def __getattr__(self, name):
        return getattr(self.sock, name)


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    s = MocketSocket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
        s.settimeout(timeout)
    # if source_address:
    #     s.bind(source_address)
    s.connect(address)
    return s


class MocketSocket(object):
    family = None
    type = None
    proto = None
    _host = None

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
        self.settimeout(socket._GLOBAL_DEFAULT_TIMEOUT)
        self.true_socket = true_socket(family, type, proto)
        self.fd = BytesIO()
        self._closed = True
        self._connected = False
        self._buflen = 1024
        self._entry = None
        self.family = family
        self.type = type
        self.proto = proto

    def gettimeout(self):
        return self.timeout

    def setsockopt(self, family, type, proto):
        self.family = family
        self.type = type
        self.proto = proto

        if self.true_socket:
            self.true_socket.setsockopt(family, type, proto)

    def settimeout(self, timeout):
        try:
            self.timeout = timeout
        except AttributeError:
            pass

    def getpeername(self):
        return self._address

    def getpeercert(self, *args, **kwargs):
        if not self._host:
            self._host, _ = self._address
        now = datetime.now()
        shift = now + timedelta(days=30 * 12)
        return {
            'notAfter': shift.strftime('%b %d %H:%M:%S GMT'),
            'subjectAltName': (
                ('DNS', '*%s' % self._host),
                ('DNS', self._host),
                ('DNS', '*'),
            ),
            'subject': (
                (
                    ('organizationName', '*.%s' % self._host),
                ),
                (
                    ('organizationalUnitName',
                     'Domain Control Validated'),
                ),
                (
                    ('commonName', '*.%s' % self._host),
                ),
            ),
        }

    def fileno(self):
        if self.true_socket:
            return self.true_socket.fileno()
        return self.fd.fileno()

    def connect(self, address):
        self._address = self._host, self._port = address
        self._closed = False

    def close(self):
        if self.true_socket and self._connected:
            self.true_socket.close()
        self._closed = True

    def makefile(self, mode='r', bufsize=-1):
        self._mode = mode
        self._bufsize = bufsize
        return self.fd

    def get_entry(self, data):
        return Mocket.get_entry(self._host, self._port, data)

    def sendall(self, data, *args, **kwargs):
        entry = self.get_entry(data)
        if not entry:
            return self.true_sendall(data, *args, **kwargs)
        entry.collect(data)
        self.fd.seek(0)
        self.fd.write(entry.get_response())
        self.fd.seek(0)

    def recv(self, buffersize, flags=None):
        resp = self.fd.readline(buffersize)
        return resp

    def _connect(self):
        if not self._connected:
            self.true_socket.connect(self._address)
            self._connected = True

    def true_sendall(self, data, *args, **kwargs):
        self._connect()
        self.true_socket.sendall(data, *args, **kwargs)
        recv = True
        written = 0
        while recv:
            recv = self.true_socket.recv(self._buflen)
            self.fd.write(recv)
            written += len(recv)
            if len(recv) < self._buflen:
                break
        self.fd.seek(- written, 1)

    def send(self, data, *args, **kwargs):
        entry = self.get_entry(data)
        if entry:
            if self._entry != entry:
                self.sendall(data, *args, **kwargs)
        self._entry = entry
        return len(data)

    def __getattr__(self, name):
        # useful when clients call methods on real
        # socket we do not provide on the fake one
        return getattr(self.true_socket, name)


class Mocket(object):
    _entries = collections.defaultdict(list)
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
        cls._entries = collections.defaultdict(list)
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
        socket.gethostname = socket.__dict__['gethostname'] = lambda: 'localhost'
        socket.gethostbyname = socket.__dict__['gethostbyname'] = lambda host: '127.0.0.1'
        socket.getaddrinfo = socket.__dict__['getaddrinfo'] = \
            lambda host, port, family=None, socktype=None, proto=None, flags=None: [(2, 1, 6, '', (host, port))]
        socket.inet_aton = socket.__dict__['inet_aton'] = socket.gethostbyname
        ssl.wrap_socket = ssl.__dict__['wrap_socket'] = FakeSSLContext.wrap_socket
        ssl.SSLSocket = ssl.__dict__['SSLSocket'] = MocketSocket
        ssl.SSLContext = ssl.__dict__['SSLSocket'] = FakeSSLContext

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
        ssl.wrap_socket = ssl.__dict__['SSLSocket'] = true_ssl_wrap_socket
        ssl.SSLSocket = ssl.__dict__['wrap_socket'] = true_ssl_socket
        ssl.SSLContext = ssl.__dict__['SSLSocket'] = true_ssl_context


class MocketEntry(object):

    class Response(byte_type):
        @property
        def data(self):
            return self

    request_cls = str
    response_cls = Response

    def __init__(self, location, responses):
        self.location = location
        self.response_index = 0

        if not isinstance(responses, collections.Iterable) or isinstance(responses, basestring):
            responses = [responses]

        lresponses = []
        for r in responses:
            if not getattr(r, 'data', False):
                if isinstance(r, text_type):
                    r = encode_utf8(r)
                r = self.response_cls(r)
            lresponses.append(r)
        else:
            if not responses:
                lresponses = [self.response_cls(encode_utf8(''))]
        self.responses = lresponses

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
        def wrapper(test, *args, **kw):
            instance = None
            if args:
                instance = args[0]
            with Mocketizer(instance):
                return test(*args, **kw)
        return decorator.decorator(wrapper, test)
mocketize = Mocketizer.wrap
