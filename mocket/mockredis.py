import shlex
from itertools import chain
from .registry import AbstractEntry, Mocket
from .mocket import CRLF


class Request(object):
    def __init__(self, data):
        self.data = data


class Response(object):
    def __init__(self, reply):
        self.reply = reply

    def __str__(self):
        return self.reply + CRLF


class Entry(AbstractEntry):
    request_cls = Request
    response_cls = Response

    def __init__(self, addr, command, responses):
        super(Entry, self).__init__(responses)

        self.command = self._redisize(command)
        self._location = addr or ('localhost', 6379)

    @classmethod
    def redis_map(cls, mapping):
        """
        >>> Entry.redis_map({'f1': 'one', 'f2': 'two'})
        ['*4', '$2', 'f1', '$3', 'one', '$2', 'f2', '$3', 'two']
        """
        d = list(chain(*tuple(mapping.items())))
        return cls._redisize_tokens(d)

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
        return cls._redisize_tokens(d)

    @staticmethod
    def _redisize_tokens(mapping):
        return ['*{0}'.format(len(mapping))] + list(chain(*zip(['${0}'.format(len(x)) for x in mapping], mapping)))

    def can_handle(self, data):
        return data.splitlines() == self.command

    @staticmethod
    def register(addr, command, *responses):
        Mocket.register(Entry(addr, command, *responses))

    @staticmethod
    def single_register(command, response, addr=None):
        Entry.register(addr, command, (Entry.response_cls(response),))
