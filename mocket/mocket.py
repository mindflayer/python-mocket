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

import urllib3
from urllib3.connection import match_hostname as urllib3_match_hostname
from urllib3.util.ssl_ import ssl_wrap_socket as urllib3_ssl_wrap_socket

try:
    from urllib3.util.ssl_ import wrap_socket as urllib3_wrap_socket
except ImportError:
    urllib3_wrap_socket = None

from .compat import basestring, byte_type, decode_from_bytes, encode_to_bytes, text_type
from .utils import (
    SSL_PROTOCOL,
    MocketMode,
    MocketSocketCore,
    get_mocketize,
    hexdump,
    hexload,
)

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

try:  # pragma: no cover
    from aiohttp import TCPConnector

    aiohttp_make_ssl_context_cache_clear = TCPConnector._make_ssl_context.cache_clear
except (ImportError, AttributeError):
    aiohttp_make_ssl_context_cache_clear = None


true_socket = socket.socket
true_create_connection = socket.create_connection
true_gethostbyname = socket.gethostbyname
true_gethostname = socket.gethostname
true_getaddrinfo = socket.getaddrinfo
true_socketpair = socket.socketpair
true_ssl_wrap_socket = getattr(
    ssl, "wrap_socket", None
)  # in Py3.12 it's only under SSLContext
true_ssl_socket = ssl.SSLSocket
true_ssl_context = ssl.SSLContext
true_inet_pton = socket.inet_pton
true_urllib3_wrap_socket = urllib3_wrap_socket
true_urllib3_ssl_wrap_socket = urllib3_ssl_wrap_socket
true_urllib3_match_hostname = urllib3_match_hostname


class SuperFakeSSLContext:
    """For Python 3.6"""

    class FakeSetter(int):
        def __set__(self, *args):
            pass

    minimum_version = FakeSetter()
    options = FakeSetter()
    verify_mode = FakeSetter(ssl.CERT_NONE)


class FakeSSLContext(SuperFakeSSLContext):
    DUMMY_METHODS = (
        "load_default_certs",
        "load_verify_locations",
        "set_alpn_protocols",
        "set_ciphers",
        "set_default_verify_paths",
    )
    sock = None
    post_handshake_auth = None
    _check_hostname = False

    @property
    def check_hostname(self):
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, *args):
        self._check_hostname = False

    def __init__(self, sock=None, server_hostname=None, _context=None, *args, **kwargs):
        self._set_dummy_methods()

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

    def _set_dummy_methods(self):
        def dummy_method(*args, **kwargs):
            pass

        for m in self.DUMMY_METHODS:
            setattr(self, m, dummy_method)

    @staticmethod
    def wrap_socket(sock=sock, *args, **kwargs):
        sock.kwargs = kwargs
        sock._secure_socket = True
        return sock

    @staticmethod
    def wrap_bio(incoming, outcoming, *args, **kwargs):
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


def socketpair(*args, **kwargs):
    """Returns a real socketpair() used by asyncio loop for supporting calls made by fastapi and similar services."""
    import _socket

    return _socket.socketpair(*args, **kwargs)


def _hash_request(h, req):
    return h(encode_to_bytes("".join(sorted(req.split("\r\n"))))).hexdigest()


class MocketSocket:
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
        self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, **kwargs
    ):
        self.true_socket = true_socket(family, type, proto)
        self._buflen = 65536
        self._entry = None
        self.family = int(family)
        self.type = int(type)
        self.proto = int(proto)
        self._truesocket_recording_dir = None
        self._did_handshake = False
        self._sent_non_empty_bytes = False
        self.kwargs = kwargs

    def __str__(self):
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

    @staticmethod
    def getsockopt(level, optname, buflen=None):
        return socket.SOCK_STREAM

    def do_handshake(self):
        self._did_handshake = True

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

    @staticmethod
    def fileno():
        if Mocket.r_fd is not None:
            return Mocket.r_fd
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
            consume_response = entry.collect(data)
            if consume_response is not False:
                response = entry.get_response()
            else:
                response = None
        else:
            response = self.true_sendall(data, *args, **kwargs)

        if response is not None:
            self.fd.seek(0)
            self.fd.write(response)
            self.fd.truncate()
            self.fd.seek(0)

    def read(self, buffersize):
        rv = self.fd.read(buffersize)
        if rv:
            self._sent_non_empty_bytes = True
        if self._did_handshake and not self._sent_non_empty_bytes:
            raise ssl.SSLWantReadError("The operation did not complete (read)")
        return rv

    def recv_into(self, buffer, buffersize=None, flags=None):
        if hasattr(buffer, "write"):
            return buffer.write(self.read(buffersize))
        # buffer is a memoryview
        data = self.read(buffersize)
        if data:
            buffer[: len(data)] = data
        return len(data)

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
        if not MocketMode().is_allowed((self._host, self._port)):
            MocketMode.raise_not_allowed()

        req = decode_from_bytes(data)
        # make request unique again
        req_signature = _hash_request(hasher, req)
        # port should be always a string
        port = text_type(self._port)

        # prepare responses dictionary
        responses = {}

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
            responses.setdefault(self._host, {})
            responses[self._host].setdefault(port, {})
            responses[self._host][port].setdefault(req_signature, {})
            response_dict = responses[self._host][port][req_signature]

        # try to get the response from the dictionary
        try:
            encoded_response = hexload(response_dict["response"])
        # if not available, call the real sendall
        except KeyError:
            host, port = self._host, self._port
            host = true_gethostbyname(host)

            if isinstance(self.true_socket, true_socket) and self._secure_socket:
                self.true_socket = true_urllib3_ssl_wrap_socket(
                    self.true_socket,
                    **self.kwargs,
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
        """Do nothing catchall function, for methods like close() and shutdown()"""

        def do_nothing(*args, **kwargs):
            pass

        return do_nothing


class Mocket:
    _address = (None, None)
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
        host = host or Mocket._address[0]
        port = port or Mocket._address[1]
        entries = cls._entries.get((host, port), [])
        for entry in entries:
            if entry.can_handle(data):
                return entry

    @classmethod
    def collect(cls, data):
        cls.request_list().append(data)

    @classmethod
    def reset(cls):
        if cls.r_fd is not None:
            os.close(cls.r_fd)
            cls.r_fd = None
        if cls.w_fd is not None:
            os.close(cls.w_fd)
            cls.w_fd = None
        cls._entries = collections.defaultdict(list)
        cls._requests = []

    @classmethod
    def last_request(cls):
        if cls.has_requests():
            return cls.request_list()[-1]

    @classmethod
    def request_list(cls):
        return cls._requests

    @classmethod
    def remove_last_request(cls):
        if cls.has_requests():
            del cls._requests[-1]

    @classmethod
    def has_requests(cls):
        return bool(cls.request_list())

    @staticmethod
    def enable(namespace=None, truesocket_recording_dir=None):
        Mocket._namespace = namespace
        Mocket._truesocket_recording_dir = truesocket_recording_dir

        if truesocket_recording_dir:
            # JSON dumps will be saved here
            if not os.path.isdir(truesocket_recording_dir):
                raise AssertionError

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
        socket.socketpair = socket.__dict__["socketpair"] = socketpair
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
        urllib3.util.ssl_wrap_socket = urllib3.util.__dict__[
            "ssl_wrap_socket"
        ] = FakeSSLContext.wrap_socket
        urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
            "ssl_wrap_socket"
        ] = FakeSSLContext.wrap_socket
        urllib3.connection.match_hostname = urllib3.connection.__dict__[
            "match_hostname"
        ] = lambda *args: None
        if pyopenssl_override:  # pragma: no cover
            # Take out the pyopenssl version - use the default implementation
            extract_from_urllib3()
        if aiohttp_make_ssl_context_cache_clear:  # pragma: no cover
            aiohttp_make_ssl_context_cache_clear()

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
        socket.socketpair = socket.__dict__["socketpair"] = true_socketpair
        if true_ssl_wrap_socket:
            ssl.wrap_socket = ssl.__dict__["wrap_socket"] = true_ssl_wrap_socket
        ssl.SSLContext = ssl.__dict__["SSLContext"] = true_ssl_context
        socket.inet_pton = socket.__dict__["inet_pton"] = true_inet_pton
        urllib3.util.ssl_.wrap_socket = urllib3.util.ssl_.__dict__[
            "wrap_socket"
        ] = true_urllib3_wrap_socket
        urllib3.util.ssl_.ssl_wrap_socket = urllib3.util.ssl_.__dict__[
            "ssl_wrap_socket"
        ] = true_urllib3_ssl_wrap_socket
        urllib3.util.ssl_wrap_socket = urllib3.util.__dict__[
            "ssl_wrap_socket"
        ] = true_urllib3_ssl_wrap_socket
        urllib3.connection.ssl_wrap_socket = urllib3.connection.__dict__[
            "ssl_wrap_socket"
        ] = true_urllib3_ssl_wrap_socket
        urllib3.connection.match_hostname = urllib3.connection.__dict__[
            "match_hostname"
        ] = true_urllib3_match_hostname
        Mocket.reset()
        if pyopenssl_override:  # pragma: no cover
            # Put the pyopenssl version back in place
            inject_into_urllib3()
        if aiohttp_make_ssl_context_cache_clear:  # pragma: no cover
            aiohttp_make_ssl_context_cache_clear()

    @classmethod
    def get_namespace(cls):
        return cls._namespace

    @classmethod
    def get_truesocket_recording_dir(cls):
        return cls._truesocket_recording_dir

    @classmethod
    def assert_fail_if_entries_not_served(cls):
        """Mocket checks that all entries have been served at least once."""
        if not all(entry._served for entry in itertools.chain(*cls._entries.values())):
            raise AssertionError("Some Mocket entries have not been served")


class MocketEntry:
    class Response(byte_type):
        @property
        def data(self):
            return self

    response_index = 0
    request_cls = byte_type
    response_cls = Response
    responses = None
    _served = None

    def __init__(self, location, responses):
        self._served = False
        self.location = location

        if not isinstance(responses, collections_abc.Iterable) or isinstance(
            responses, basestring
        ):
            responses = [responses]

        if not responses:
            self.responses = [self.response_cls(encode_to_bytes(""))]
        else:
            self.responses = []
            for r in responses:
                if not isinstance(r, BaseException) and not getattr(r, "data", False):
                    if isinstance(r, text_type):
                        r = encode_to_bytes(r)
                    r = self.response_cls(r)
                self.responses.append(r)

    def __repr__(self):
        return "{}(location={})".format(self.__class__.__name__, self.location)

    @staticmethod
    def can_handle(data):
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


class Mocketizer:
    def __init__(
        self,
        instance=None,
        namespace=None,
        truesocket_recording_dir=None,
        strict_mode=False,
        strict_mode_allowed=None,
    ):
        self.instance = instance
        self.truesocket_recording_dir = truesocket_recording_dir
        self.namespace = namespace or text_type(id(self))
        MocketMode().STRICT = strict_mode
        if strict_mode:
            MocketMode().STRICT_ALLOWED = strict_mode_allowed or []
        elif strict_mode_allowed:
            raise ValueError(
                "Allowed locations are only accepted when STRICT mode is active."
            )

    def enter(self):
        Mocket.enable(
            namespace=self.namespace,
            truesocket_recording_dir=self.truesocket_recording_dir,
        )
        if self.instance:
            self.check_and_call("mocketize_setup")

    def __enter__(self):
        self.enter()
        return self

    def exit(self):
        if self.instance:
            self.check_and_call("mocketize_teardown")
        Mocket.disable()

    def __exit__(self, type, value, tb):
        self.exit()

    async def __aenter__(self, *args, **kwargs):
        self.enter()
        return self

    async def __aexit__(self, *args, **kwargs):
        self.exit()

    def check_and_call(self, method_name):
        method = getattr(self.instance, method_name, None)
        if callable(method):
            method()

    @staticmethod
    def factory(test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args):
        instance = args[0] if args else None
        namespace = None
        if truesocket_recording_dir:
            namespace = ".".join(
                (
                    instance.__class__.__module__,
                    instance.__class__.__name__,
                    test.__name__,
                )
            )

        return Mocketizer(
            instance,
            namespace=namespace,
            truesocket_recording_dir=truesocket_recording_dir,
            strict_mode=strict_mode,
            strict_mode_allowed=strict_mode_allowed,
        )


def wrapper(
    test,
    truesocket_recording_dir=None,
    strict_mode=False,
    strict_mode_allowed=None,
    *args,
    **kwargs,
):
    with Mocketizer.factory(
        test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args
    ):
        return test(*args, **kwargs)


mocketize = get_mocketize(wrapper_=wrapper)
