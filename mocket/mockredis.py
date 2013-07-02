import shlex
from itertools import chain
from mocket import Mocket, MocketEntry, CRLF


def redisize_tokens(mapping):
    """
    >>> redisize_tokens({'f1': 'one', 'f2': 'two'})
    ['*2', '$2', 'f1', '$2', 'f2']
    """
    return ['*{0}'.format(len(mapping))] + list(chain(*zip(['${0}'.format(len(x)) for x in mapping], mapping)))


class Request(object):
    def __init__(self, data):
        self.data = data


class Response(object):
    def __init__(self, reply):
        self.reply = reply

    def __str__(self):
        return self.redisize(self.reply)

    @staticmethod
    def redisize(data):
        r"""
        >>> Response.redisize(10)
        ':10\r\n'
        >>> Response.redisize({'f1': 'one', 'f2': 'two'})
        '*4\r\n$2\r\nf1\r\n$3\r\none\r\n$2\r\nf2\r\n$3\r\ntwo\r\n'
        >>> Response.redisize('+OK')
        '+OK\r\n'
        """
        CONVERSION = {
            dict: lambda x: CRLF.join(redisize_tokens(list(chain(*tuple(data.items()))))),
            int: lambda x: ':{0}'.format(x),
        }
        return CONVERSION.get(type(data), lambda x: x)(data) + CRLF


class Entry(MocketEntry):
    request_cls = Request
    response_cls = Response

    def __init__(self, addr, command, responses):
        super(Entry, self).__init__(addr or ('localhost', 6379), responses)
        self.command = self._redisize(command)

    @classmethod
    def _redisize(cls, command):
        """
        >>> Entry._redisize('SET "mocket" "is awesome!"')
        ['*3', '$3', 'SET', '$6', 'mocket', '$11', 'is awesome!']
        >>> Entry._redisize('set "mocket" "is awesome!"')
        ['*3', '$3', 'SET', '$6', 'mocket', '$11', 'is awesome!']
        """
        d = shlex.split(command)
        d[0] = d[0].upper()
        return redisize_tokens(d)

    def can_handle(self, data):
        return data.splitlines() == self.command

    @staticmethod
    def register(addr, command, *responses):
        responses = [Entry.response_cls(r) for r in responses]
        Mocket.register(Entry(addr, command, responses))

    @staticmethod
    def single_register(command, response, addr=None):
        Entry.register(addr, command, response)

    @staticmethod
    def multi_register(command, responses, addr=None):
        Entry.register(addr, command, *responses)
