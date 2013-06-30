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

    @staticmethod
    def _redisize(command):
        """
        >>> Entry._redisize('SET "mocket" "is awesome!"')
        ['*3', '$3', 'SET', '$6', 'mocket', '$11', 'is awesome!']
        """

        d = shlex.split(command)
        return ['*{0}'.format(len(d))] + list(chain(*zip(['${0}'.format(len(x)) for x in d], d)))

    def can_handle(self, data):
        print data.splitlines(), self.command
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