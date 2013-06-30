import functools
import socket
from .mocket import *


class Mocket(object):
    _entries = {}
    _requests = []

    @classmethod
    def register(cls, *entries):
        for entry in entries:
            if entry._location not in cls._entries:
                cls._entries[entry._location] = []
            cls._entries[entry._location].append(entry)

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
    def remove_last(cls):
        if cls._requests:
            del cls._requests[-1]

    @classmethod
    def reset(cls):
        cls._entries = {}
        cls._requests = []

    @classmethod
    def last_request(cls):
        if cls._requests:
            return cls._requests[-1]

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


class AbstractEntry(object):
    request_cls = NotImplemented
    response_cls = NotImplemented

    def __init__(self, responses):
        self.responses = responses or (self.response_cls(),)
        self.response_index = 0
        self._location = NotImplemented

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
