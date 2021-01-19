import collections
import collections.abc as collections_abc
import errno
import hashlib
import io
import itertools
import json
import os
import select
import socket
import ssl
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError

import decorator
import urllib3
from urllib3.util.ssl_ import ssl_wrap_socket as urllib3_ssl_wrap_socket
from urllib3.util.ssl_ import wrap_socket as urllib3_wrap_socket

from .compat import basestring, byte_type, decode_from_bytes, encode_to_bytes, text_type
from .utils import SSL_PROTOCOL, MocketSocketCore, hexdump, hexload, wrap_ssl_socket

xxh32 = None
try:
    from xxhash import xxh32
except ImportError:  # pragma: no cover
    try:
        from xxhash_cffi import xxh32
    except ImportError:
        pass
hasher = xxh32 or hashlib.md5

try:  # pragma: no cover
    from urllib3.contrib.pyopenssl import extract_from_urllib3, inject_into_urllib3

    pyopenssl_override = True
except ImportError:
    pyopenssl_override = False


true_socket = socket.socket
true_create_connection = socket.create_connection
true_gethostbyname = socket.gethostbyname
true_gethostname = socket.gethostname
true_getaddrinfo = socket.getaddrinfo
true_ssl_wrap_socket = ssl.wrap_socket
true_ssl_socket = ssl.SSLSocket
true_ssl_context = ssl.SSLContext
true_inet_pton = socket.inet_pton
true_urllib3_wrap_socket = urllib3_wrap_socket
true_urllib3_ssl_wrap_socket = urllib3_ssl_wrap_socket


class SuperFakeSSLContext(object):
    """ For Python 3.6 """

    class FakeSetter(int):
        def __set__(self, *args):
            pass

    options = FakeSetter()
    verify_mode = FakeSetter(ssl.CERT_OPTIONAL)


class FakeSSLContext(SuperFakeSSLContext):
    sock = None
    post_handshake_auth = None

    def __init__(self, sock=None, server_hostname=None, _context=None, *args, **kwargs):
        if isinstance(sock, MocketSocket):
            self.sock = sock
            self.sock._host = server_hostname
            self.sock.true_socket = true_ssl_socket(
                sock=self.sock.true_socket,
                server_hostname=server_hostname,
                _context=true_ssl_context(protocol=SSL_PROTOCOL),
            )
        elif isinstance(sock, int) and true_ssl_context:
            self.context = true_ssl_context(sock)

    @staticmethod
    def load_default_certs(*args, **kwargs):
        pass

    @staticmethod
    def load_verify_locations(*args, **kwargs):
        pass

    @staticmethod
    def wrap_socket(sock=sock, *args, **kwargs):
        sock.kwargs = kwargs
        sock._secure_socket = True
        return sock

    def wrap_bio(self, incoming, outcoming, *args, **kwargs):
        ssl_obj = MocketSocket()
        ssl_obj._host = kwargs["server_hostname"]
        return ssl_obj

    def __getattr__(self, name):
        if self.sock is not None:
            return getattr(self.sock, name)


def create_connection(address, timeout=None, source_address=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout:
        s.settimeout(timeout)
    s.connect(address)
    return s


def _hash_request(h, req):
    return h(encode_to_bytes("".join(sorted(req.split("\r\n"))))).hexdigest()


class MocketSocket(object):
    timeout = None
    _fd = None
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
    _secure_socket = False

    def __init__(
        self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, *args, **kwargs
    ):
        self.true_socket = true_socket(family, type, proto)
        self._buflen = 65536
        self._entry = None
        self.family = int(family)
        self.type = int(type)
        self.proto = int(proto)
        self._truesocket_recording_dir = None
        self.kwargs = kwargs

        sock = kwargs.get("sock")
        if sock is not None:
            self.__dict__ = dict(sock.__dict__)

            self.true_socket = wrap_ssl_socket(
                true_ssl_socket,
                self.true_socket,
                true_ssl_context(protocol=SSL_PROTOCOL),
            )

    def __unicode__(self):  # pragma: no cover
        return str(self)

    def __str__(self):  # pragma: no cover
        return "({})(family={} type={} protocol={})".format(
            self.__class__.__name__, self.family, self.type, self.proto
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def fd(self):
        if self._fd is None:
            self._fd = MocketSocketCore()
        return self._fd

    def gettimeout(self):
        return self.timeout

    def setsockopt(self, family, type, proto):
        self.family = family
        self.type = type
        self.proto = proto

        if self.true_socket:
            self.true_socket.setsockopt(family, type, proto)

    def settimeout(self, timeout):
        self.timeout = timeout

    def getsockopt(self, level, optname, buflen=None):
        return socket.SOCK_STREAM

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
            "notAfter": shift.strftime("%b %d %H:%M:%S GMT"),
            "subjectAltName": (
                ("DNS", "*.%s" % self._host),
                ("DNS", self._host),
                ("DNS", "*"),
            ),
            "subject": (
                (("organizationName", "*.%s" % self._host),),
                (("organizationalUnitName", "Domain Control Validated"),),
                (("commonName", "*.%s" % self._host),),
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

    def makefile(self, mode="r", bufsize=-1):
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

    def recv_into(self, buffer, buffersize=None, flags=None):
        return buffer.write(self.read(buffersize))

    def recv(self, buffersize, flags=None):
        if Mocket.r_fd and Mocket.w_fd:
            return os.read(Mocket.r_fd, buffersize)
        data = self.read(buffersize)
        if data:
            return data
        # used by Redis mock
        exc = BlockingIOError()
        exc.errno = errno.EWOULDBLOCK
        exc.args = (0,)
        raise exc

    def true_sendall(self, data, *args, **kwargs):
        req = decode_from_bytes(data)
        # make request unique again
        req_signature = _hash_request(hasher, req)
        # port should be always a string
        port = text_type(self._port)

        # prepare responses dictionary
        responses = dict()

        if Mocket.get_truesocket_recording_dir():
            path = os.path.join(
                Mocket.get_truesocket_recording_dir(), Mocket.get_namespace() + ".json"
            )
            # check if there's already a recorded session dumped to a JSON file
            try:
                with io.open(path) as f:
                    responses = json.load(f)
            # if not, create a new dictionary
            except (FileNotFoundError, JSONDecodeError):
                pass

        try:
            try:
                response_dict = responses[self._host][port][req_signature]
            except KeyError:
                if hasher is not hashlib.md5:
                    # Fallback for backwards compatibility
                    req_signature = _hash_request(hashlib.md5, req)
                    response_dict = responses[self._host][port][req_signature]
                else:
                    raise
        except KeyError:
            # preventing next KeyError exceptions
            responses.setdefault(self._host, dict())
            responses[self._host].setdefault(port, dict())
            responses[self._host][port].setdefault(req_signature, dict())
            response_dict = responses[self._host][port][req_signature]

        # try to get the response from the dictionary
        try:
            encoded_response = hexload(response_dict["response"])
        # if not available, call the real sendall
        except KeyError:
            host, port = Mocket._address
            host = true_gethostbyname(host)

            if isinstance(self.true_socket, true_socket) and self._secure_socket:
                try:
                    self = MocketSocket(sock=self)
                except TypeError:
                    ssl_context = self.kwargs.get("ssl_context")
                    server_hostname = self.kwargs.get("server_hostname")
                    self.true_socket = true_ssl_context.wrap_socket(
                        self=ssl_context,
                        sock=self.true_socket,
                        server_hostname=server_hostname,
                    )

            try:
                self.true_socket.connect((host, port))
            except (OSError, socket.error, ValueError):
                # already connected
                pass
            self.true_socket.sendall(data, *args, **kwargs)
            encoded_response = b""
            # https://github.com/kennethreitz/requests/blob/master/tests/testserver/server.py#L13
            while True:
                if (
                    not select.select([self.true_socket], [], [], 0.1)[0]
                    and encoded_response
                ):
                    break
                recv = self.true_socket.recv(self._buflen)

                if not recv and encoded_response:
                    break
                encoded_response += recv

            # dump the resulting dictionary to a JSON file
            if Mocket.get_truesocket_recording_dir():

                # update the dictionary with request and response lines
                response_dict["request"] = req
                response_dict["response"] = hexdump(encoded_response)

                with io.open(path, mode="w") as f:
                    f.write(
                        decode_from_bytes(
                            json.dumps(responses, indent=4, sort_keys=True)
                        )
                    )

        # response back to .sendall() which writes it to the Mocket socket and flush the BytesIO
        return encoded_response

    def send(self, data, *args, **kwargs):  # pragma: no cover
        entry = self.get_entry(data)
        if not entry or (entry and self._entry != entry):
            self.sendall(data, entry=entry, *args, **kwargs)
        else:
            req = Mocket.last_request()
            if hasattr(req, "add_data"):
                req.add_data(data)
        self._entry = entry
        return len(data)

    def close(self):
        if self.true_socket and not self.true_socket._closed:
            self.true_socket.close()
        self._fd = None

    def __getattr__(self, name):
        """ Do nothing catchall function, for methods like close() and shutdown() """

        def do_nothing(*args, **kwargs):
            pass

        return do_nothing


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
        cls.r_fd = None
        cls.w_fd = None
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

    @classmethod
    def has_requests(cls):
        return len(cls._requests) > 0

    @staticmethod
    def enable(namespace=None, truesocket_recording_dir=None):
        Mocket._namespace = namespace
        Mocket._truesocket_recording_dir = truesocket_recording_dir

        if truesocket_recording_dir:
            # JSON dumps will be saved here
            assert os.path.isdir(truesocket_recording_dir)

        socket.socket = socket.__dict__["socket"] = MocketSocket
        socket._socketobject = socket.__dict__["_socketobject"] = MocketSocket
        socket.SocketType = socket.__dict__["SocketType"] = MocketSocket
        socket.create_connection = socket.__dict__[
            "create_connection"
        ] = create_connection
        socket.gethostname = socket.__dict__["gethostname"] = lambda: "localhost"
        socket.gethostbyname = socket.__dict__[
            "gethostbyname"
        ] = lambda host: "127.0.0.1"
        socket.getaddrinfo = socket.__dict__[
            "getaddrinfo"
        ] = lambda host, port, family=None, socktype=None, proto=None, flags=None: [
            (2, 1, 6, "", (host, port))
        ]
        ssl.wrap_socket = ssl.__dict__["wrap_socket"] = FakeSSLContext.wrap_socket
        ssl.SSLContext = ssl.__dict__["SSLContext"] = FakeSSLContext
        socket.inet_pton = socket.__dict__["inet_pton"] = lambda family, ip: byte_type(
            "\x7f\x00\x00\x01", "utf-8"
        )
        urllib3.util.ssl_.wrap_socket = urllib3.util.ssl_.__dict__[
            "wrap_socket"
        ] = FakeSSLContext.wrap_socket
        urllib3.util.ssl_.ssl_wrap_socket = urllib3.util.ssl_.__dict__[
            "ssl_wrap_socket"
        ] = FakeSSLContext.wrap_socket
        urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
            "ssl_wrap_socket"
        ] = FakeSSLContext.wrap_socket
        if pyopenssl_override:  # pragma: no cover
            # Take out the pyopenssl version - use the default implementation
            extract_from_urllib3()

    @staticmethod
    def disable():
        socket.socket = socket.__dict__["socket"] = true_socket
        socket._socketobject = socket.__dict__["_socketobject"] = true_socket
        socket.SocketType = socket.__dict__["SocketType"] = true_socket
        socket.create_connection = socket.__dict__[
            "create_connection"
        ] = true_create_connection
        socket.gethostname = socket.__dict__["gethostname"] = true_gethostname
        socket.gethostbyname = socket.__dict__["gethostbyname"] = true_gethostbyname
        socket.getaddrinfo = socket.__dict__["getaddrinfo"] = true_getaddrinfo
        ssl.wrap_socket = ssl.__dict__["wrap_socket"] = true_ssl_wrap_socket
        ssl.SSLContext = ssl.__dict__["SSLContext"] = true_ssl_context
        socket.inet_pton = socket.__dict__["inet_pton"] = true_inet_pton
        urllib3.util.ssl_.wrap_socket = urllib3.util.ssl_.__dict__[
            "wrap_socket"
        ] = true_urllib3_wrap_socket
        urllib3.util.ssl_.ssl_wrap_socket = urllib3.util.ssl_.__dict__[
            "ssl_wrap_socket"
        ] = true_urllib3_ssl_wrap_socket
        urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
            "ssl_wrap_socket"
        ] = true_urllib3_ssl_wrap_socket
        Mocket.reset()
        if pyopenssl_override:  # pragma: no cover
            # Put the pyopenssl version back in place
            inject_into_urllib3()

    @classmethod
    def get_namespace(cls):
        return cls._namespace

    @classmethod
    def get_truesocket_recording_dir(cls):
        return cls._truesocket_recording_dir

    @classmethod
    def assert_fail_if_entries_not_served(cls):
        """ Mocket checks that all entries have been served at least once. """
        assert all(
            entry._served for entry in itertools.chain(*cls._entries.values())
        ), "Some Mocket entries have not been served"


class MocketEntry(object):
    class Response(byte_type):
        @property
        def data(self):
            return self

    request_cls = str
    response_cls = Response
    responses = None
    _served = None

    def __init__(self, location, responses):
        self._served = False
        self.location = location
        self.response_index = 0

        if not isinstance(responses, collections_abc.Iterable) or isinstance(
            responses, basestring
        ):
            responses = [responses]

        self.responses = []
        for r in responses:
            if isinstance(r, BaseException):
                pass
            elif not getattr(r, "data", False):
                if isinstance(r, text_type):
                    r = encode_to_bytes(r)
                r = self.response_cls(r)
            self.responses.append(r)
        else:
            if not responses:
                self.responses = [self.response_cls(encode_to_bytes(""))]

    def can_handle(self, data):
        return True

    def collect(self, data):
        req = self.request_cls(data)
        Mocket.collect(req)

    def get_response(self):
        response = self.responses[self.response_index]
        if self.response_index < len(self.responses) - 1:
            self.response_index += 1

        self._served = True

        if isinstance(response, BaseException):
            raise response

        return response.data


class Mocketizer(object):
    def __init__(self, instance=None, namespace=None, truesocket_recording_dir=None):
        self.instance = instance
        self.truesocket_recording_dir = truesocket_recording_dir
        self.namespace = namespace or text_type(id(self))

    def __enter__(self):
        Mocket.enable(
            namespace=self.namespace,
            truesocket_recording_dir=self.truesocket_recording_dir,
        )
        if self.instance:
            self.check_and_call("mocketize_setup")
        return self

    def __exit__(self, type, value, tb):
        if self.instance:
            self.check_and_call("mocketize_teardown")
        Mocket.disable()

    def check_and_call(self, method):
        method = getattr(self.instance, method, None)
        if callable(method):
            method()

    @classmethod
    def wrap(cls, test=None, truesocket_recording_dir=None):
        def wrapper(t, *args, **kw):
            instance = args[0] if args else None
            namespace = None
            if truesocket_recording_dir:
                namespace = ".".join(
                    (
                        instance.__class__.__module__,
                        instance.__class__.__name__,
                        t.__name__,
                    )
                )
            with cls(
                instance,
                namespace=namespace,
                truesocket_recording_dir=truesocket_recording_dir,
            ):
                t(*args, **kw)
            return wrapper

        return decorator.decorator(wrapper, test)


mocketize = Mocketizer.wrap
