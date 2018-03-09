# coding=utf-8
from __future__ import unicode_literals
import socket
import json
import os
import ssl
import io
import collections
import hashlib
import select
from datetime import datetime, timedelta

import decorator
import hexdump

from .utils import (
    MocketSocketCore,
)
from .compat import (
    encode_to_bytes,
    decode_from_bytes,
    basestring,
    byte_type,
    text_type,
    FileNotFoundError,
    JSONDecodeError,
)

__all__ = (
    'true_socket',
    'true_create_connection',
    'true_gethostbyname',
    'true_gethostname',
    'true_getaddrinfo',
    'true_ssl_wrap_socket',
    'true_ssl_socket',
    'true_ssl_context',
    'true_inet_pton',
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
true_ssl_context = ssl.SSLContext
true_inet_pton = socket.inet_pton


class SuperFakeSSLContext(object):
    """ For Python 3.6 """
    class FakeSetter(int):
        def __set__(self, *args):
            pass
    options = FakeSetter()
    verify_mode = FakeSetter(ssl.CERT_OPTIONAL)


class FakeSSLContext(SuperFakeSSLContext):
    sock = None

    def __init__(self, sock=None, server_hostname=None, _context=None, *args, **kwargs):
        if isinstance(sock, MocketSocket):
            self.sock = sock
            self.sock._host = server_hostname
            if true_ssl_context:
                self.sock.true_socket = true_ssl_socket(
                    sock=self.sock.true_socket,
                    server_hostname=server_hostname,
                    _context=true_ssl_context(
                        protocol=ssl.PROTOCOL_SSLv23,
                    )
                )
            else:  # Python 2.
                self.sock.true_socket = true_ssl_socket(
                    sock=self.sock.true_socket,
                )
        elif isinstance(sock, int) and true_ssl_context:
            self.context = true_ssl_context(sock)

    @staticmethod
    def load_default_certs(*args, **kwargs):
        pass

    @staticmethod
    def wrap_socket(sock=sock, *args, **kwargs):
        return sock

    def wrap_bio(self, incoming, outcoming, *args, **kwargs):
        ssl_obj = MocketSocket()
        ssl_obj._host = kwargs['server_hostname']
        return ssl_obj

    def __getattr__(self, name):
        return getattr(self.sock, name)


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
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
    _port = None
    _address = None
    cipher = lambda s: ("ADH", "AES256", "SHA")
    compression = lambda s: ssl.OP_NO_COMPRESSION
    _mode = None
    _bufsize = None

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, detach=None):
        self.settimeout(socket._GLOBAL_DEFAULT_TIMEOUT)
        self.true_socket = true_socket(family, type, proto)
        self.fd = MocketSocketCore()
        self._connected = False
        self._buflen = 65536
        self._entry = None
        self.family = int(family)
        self.type = int(type)
        self.proto = int(proto)
        self._truesocket_recording_dir = None

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return "({})(family={} type={} protocol={})".format(
            self.__class__.__name__, self.family, self.type, self.proto
        )

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

    def do_handshake(self):
        pass

    def getpeername(self):
        return self._address

    def setblocking(self, block):
        self.settimeout(None) if block else self.settimeout(0.0)

    def getsockname(self):
        return socket.gethostbyname(self._address[0]), self._address[1]

    def getpeercert(self, *args, **kwargs):
        if not (self._host and self._port):
            self._address = self._host, self._port = Mocket._address

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

    def unwrap(self):
        return self

    def write(self, data):
        return self.send(encode_to_bytes(data))

    def fileno(self):
        Mocket.r_fd, Mocket.w_fd = os.pipe()
        return Mocket.r_fd

    def connect(self, address):
        self._address = self._host, self._port = address
        Mocket._address = address

    def makefile(self, mode='r', bufsize=-1):
        self._mode = mode
        self._bufsize = bufsize
        return self.fd

    def get_entry(self, data):
        return Mocket.get_entry(self._host, self._port, data)

    def sendall(self, data, entry=None, *args, **kwargs):
        if entry is None:
            entry = self.get_entry(data)

        if entry:
            entry.collect(data)
            response = entry.get_response()
        else:
            response = self.true_sendall(data, *args, **kwargs)

        self.fd.seek(0)
        self.fd.write(response)
        self.fd.truncate()
        self.fd.seek(0)

    def read(self, buffersize):
        return self.fd.read(buffersize)

    def recv(self, buffersize, flags=None):
        if Mocket.r_fd and Mocket.w_fd:
            return os.read(Mocket.r_fd, buffersize)
        return self.fd.read(buffersize)

    def _connect(self):  # pragma: no cover
        if not self._connected:
            self.true_socket.connect(Mocket._address)
            self._connected = True

    def true_sendall(self, data, *args, **kwargs):
        req = decode_from_bytes(data)
        # make request unique again
        req_signature = hashlib.md5(encode_to_bytes(''.join(sorted(req.split('\r\n'))))).hexdigest()
        # port should be always a string
        port = text_type(self._port)

        # prepare responses dictionary
        responses = dict()

        if Mocket.get_truesocket_recording_dir():
            path = os.path.join(
                Mocket.get_truesocket_recording_dir(),
                Mocket.get_namespace() + '.json',
            )
            # check if there's already a recorded session dumped to a JSON file
            try:
                with io.open(path) as f:
                    responses = json.load(f)
            # if not, create a new dictionary
            except (FileNotFoundError, JSONDecodeError):
                pass

        try:
            response_dict = responses[self._host][port][req_signature]
        except KeyError:
            # preventing next KeyError exceptions
            responses.setdefault(self._host, dict())
            responses[self._host].setdefault(port, dict())
            responses[self._host][port].setdefault(req_signature, dict())
            response_dict = responses[self._host][port][req_signature]

        # try to get the response from the dictionary
        try:
            try:
                encoded_response = hexdump.dehex(response_dict['response'])
            except TypeError:  # pragma: no cover
                # Python 2
                encoded_response = hexdump.restore(encode_to_bytes(response_dict['response']))
        # if not available, call the real sendall
        except KeyError:
            self._connect()
            self.true_socket.sendall(data, *args, **kwargs)
            encoded_response = b''
            # https://github.com/kennethreitz/requests/blob/master/tests/testserver/server.py#L13
            while select.select([self.true_socket], [], [], 0.5)[0]:
                recv = self.true_socket.recv(self._buflen)
                if recv:
                    encoded_response += recv
                else:
                    break

            # dump the resulting dictionary to a JSON file
            if Mocket.get_truesocket_recording_dir():

                # update the dictionary with request and response lines
                response_dict['request'] = req
                response_dict['response'] = hexdump.dump(encoded_response)

                with io.open(path, mode='w') as f:
                    f.write(decode_from_bytes(json.dumps(responses, indent=4, sort_keys=True)))

        # response back to .sendall() which writes it to the mocket socket and flush the BytesIO
        return encoded_response

    def send(self, data, *args, **kwargs):  # pragma: no cover
        entry = self.get_entry(data)
        if entry and self._entry != entry:
            self.sendall(data, entry=entry, *args, **kwargs)
        else:
            req = Mocket.last_request()
            if hasattr(req, 'add_data'):
                req.add_data(decode_from_bytes(data))
        self._entry = entry
        return len(data)

    def __getattr__(self, name):
        """ Useful when clients call methods on real
        socket we do not provide on the fake one. """
        return getattr(self.true_socket, name)  # pragma: no cover


class Mocket(object):
    _entries = collections.defaultdict(list)
    _requests = []
    _namespace = text_type(id(_entries))
    _truesocket_recording_dir = None
    r_fd = None
    w_fd = None

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
    def enable(namespace=None, truesocket_recording_dir=None):
        Mocket._namespace = namespace
        Mocket._truesocket_recording_dir = truesocket_recording_dir

        if truesocket_recording_dir:
            # JSON dumps will be saved here
            assert os.path.isdir(truesocket_recording_dir)

        socket.socket = socket.__dict__['socket'] = MocketSocket
        socket._socketobject = socket.__dict__['_socketobject'] = MocketSocket
        socket.SocketType = socket.__dict__['SocketType'] = MocketSocket
        ssl.SSLSocket = ssl.__dict__['SSLSocket'] = MocketSocket
        socket.create_connection = socket.__dict__['create_connection'] = create_connection
        socket.gethostname = socket.__dict__['gethostname'] = lambda: 'localhost'
        socket.gethostbyname = socket.__dict__['gethostbyname'] = lambda host: '127.0.0.1'
        socket.getaddrinfo = socket.__dict__['getaddrinfo'] = \
            lambda host, port, family=None, socktype=None, proto=None, flags=None: [(2, 1, 6, '', (host, port))]
        ssl.wrap_socket = ssl.__dict__['wrap_socket'] = FakeSSLContext.wrap_socket
        ssl.SSLContext = ssl.__dict__['SSLSocket'] = FakeSSLContext
        socket.inet_pton = socket.__dict__['inet_pton'] = lambda family, ip: byte_type(
            '\x7f\x00\x00\x01',
            'utf-8'
        )

    @staticmethod
    def disable():
        socket.socket = socket.__dict__['socket'] = true_socket
        socket._socketobject = socket.__dict__['_socketobject'] = true_socket
        socket.SocketType = socket.__dict__['SocketType'] = true_socket
        socket.create_connection = socket.__dict__['create_connection'] = true_create_connection
        socket.gethostname = socket.__dict__['gethostname'] = true_gethostname
        socket.gethostbyname = socket.__dict__['gethostbyname'] = true_gethostbyname
        socket.getaddrinfo = socket.__dict__['getaddrinfo'] = true_getaddrinfo
        ssl.wrap_socket = ssl.__dict__['wrap_socket'] = true_ssl_wrap_socket
        ssl.SSLSocket = ssl.__dict__['SSLSocket'] = true_ssl_socket
        ssl.SSLContext = ssl.__dict__['SSLContext'] = true_ssl_context
        socket.inet_pton = socket.__dict__['inet_pton'] = true_inet_pton

    @classmethod
    def get_namespace(cls):
        return cls._namespace

    @classmethod
    def get_truesocket_recording_dir(cls):
        return cls._truesocket_recording_dir


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
                    r = encode_to_bytes(r)
                r = self.response_cls(r)
            lresponses.append(r)
        else:
            if not responses:
                lresponses = [self.response_cls(encode_to_bytes(''))]
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
    def __init__(self, instance=None, namespace=None, truesocket_recording_dir=None):
        self.instance = instance
        self.truesocket_recording_dir = truesocket_recording_dir
        self.namespace = namespace or text_type(id(self))

    def __enter__(self):
        Mocket.enable(namespace=self.namespace, truesocket_recording_dir=self.truesocket_recording_dir)
        if self.instance:
            self.check_and_call('mocketize_setup')

    def __exit__(self, type, value, tb):
        if self.instance:
            self.check_and_call('mocketize_teardown')
        Mocket.disable()
        Mocket.reset()

    def check_and_call(self, method):
        method = getattr(self.instance, method, None)
        if callable(method):
            method()

    @staticmethod
    def wrap(test=None, truesocket_recording_dir=None):
        def wrapper(t, *args, **kw):
            instance = args[0] if args else None
            namespace = '.'.join((instance.__class__.__module__, instance.__class__.__name__, t.__name__))
            with Mocketizer(instance, namespace=namespace, truesocket_recording_dir=truesocket_recording_dir):
                t(*args, **kw)
            return wrapper
        return decorator.decorator(wrapper, test)


mocketize = Mocketizer.wrap
