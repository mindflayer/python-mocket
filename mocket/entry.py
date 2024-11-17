import collections.abc

from mocket.compat import encode_to_bytes
from mocket.mocket import Mocket


class MocketEntry:
    class Response(bytes):
        @property
        def data(self):
            return self

    response_index = 0
    request_cls = bytes
    response_cls = Response
    responses = None
    _served = None

    def __init__(self, location, responses):
        self._served = False
        self.location = location

        if not isinstance(responses, collections.abc.Iterable):
            responses = [responses]

        if not responses:
            self.responses = [self.response_cls(encode_to_bytes(""))]
        else:
            self.responses = []
            for r in responses:
                if not isinstance(r, BaseException) and not getattr(r, "data", False):
                    if isinstance(r, str):
                        r = encode_to_bytes(r)
                    r = self.response_cls(r)
                self.responses.append(r)

    def __repr__(self):
        return f"{self.__class__.__name__}(location={self.location})"

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
