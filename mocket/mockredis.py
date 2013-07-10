# coding=utf-8
from __future__ import unicode_literals
from itertools import chain
from .compat import text_type, byte_type, encode_utf8, decode_utf8, shsplit
from .mocket import MocketEntry, Mocket


class Request(object):
    def __init__(self, data):
        self.data = data


class Response(object):
    def __init__(self, data=None):
        self.data = Redisizer.redisize(data or OK)


class Redisizer(byte_type):
    @staticmethod
    def tokens(iterable):
        iterable = [encode_utf8(x) for x in iterable]
        return ['*{0}'.format(len(iterable)).encode('utf-8')] + list(chain(*zip(['${0}'.format(len(x)).encode('utf-8') for x in iterable], iterable)))

    @staticmethod
    def redisize(data):
        if isinstance(data, Redisizer):
            return data
        if isinstance(data, byte_type):
            data = decode_utf8(data)
        CONVERSION = {
            dict: lambda x: b'\r\n'.join(Redisizer.tokens(list(chain(*tuple(x.items()))))),
            int: lambda x: ':{0}'.format(x).encode('utf-8'),
            text_type: lambda x: '${0}\r\n{1}'.format(len(x.encode('utf-8')), x).encode('utf-8'),
            list: lambda x: b'\r\n'.join(Redisizer.tokens(x)),
        }
        return Redisizer(CONVERSION[type(data)](data) + b'\r\n')

    @staticmethod
    def command(description, _type='+'):
        return Redisizer('{0}{1}{2}'.format(_type, description, '\r\n').encode('utf-8'))

    @staticmethod
    def error(description):
        return Redisizer.command(description, _type='-')
OK = Redisizer.command('OK')
QUEUED = Redisizer.command('QUEUED')
ERROR = Redisizer.error


class Entry(MocketEntry):
    request_cls = Request
    response_cls = Response

    def __init__(self, addr, command, responses):
        super(Entry, self).__init__(addr or ('localhost', 6379), responses)
        d = shsplit(command)
        d[0] = d[0].upper()
        self.command = Redisizer.tokens(d)

    def can_handle(self, data):
        return data.splitlines() == self.command

    @staticmethod
    def register(addr, command, *responses):
        responses = [Entry.response_cls(r) for r in responses]
        Mocket.register(Entry(addr, command, responses))

    @staticmethod
    def register_response(command, response, addr=None):
        Entry.register(addr, command, response)

    @staticmethod
    def register_responses(command, responses, addr=None):
        Entry.register(addr, command, *responses)
