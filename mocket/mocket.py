import collections
import itertools
import os
from typing import Optional, Tuple

import mocket.inject

# NOTE this is here for backwards-compat to keep old import-paths working
from mocket.socket import MocketSocket as MocketSocket


class Mocket:
    _socket_pairs = {}
    _address = (None, None)
    _entries = collections.defaultdict(list)
    _requests = []
    _namespace = str(id(_entries))
    _truesocket_recording_dir = None

    @classmethod
    def get_pair(cls, address: tuple) -> Tuple[Optional[int], Optional[int]]:
        """
        Given the id() of the caller, return a pair of file descriptors
        as a tuple of two integers: (<read_fd>, <write_fd>)
        """
        return cls._socket_pairs.get(address, (None, None))

    @classmethod
    def set_pair(cls, address: tuple, pair: Tuple[int, int]) -> None:
        """
        Store a pair of file descriptors under the key `id_`
        as a tuple of two integers: (<read_fd>, <write_fd>)
        """
        cls._socket_pairs[address] = pair

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
        for r_fd, w_fd in cls._socket_pairs.values():
            os.close(r_fd)
            os.close(w_fd)
        cls._socket_pairs = {}
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

    @classmethod
    def get_namespace(cls):
        return cls._namespace

    @staticmethod
    def enable(namespace=None, truesocket_recording_dir=None):
        mocket.inject.enable(namespace, truesocket_recording_dir)

    @staticmethod
    def disable():
        mocket.inject.disable()

    @classmethod
    def get_truesocket_recording_dir(cls):
        return cls._truesocket_recording_dir

    @classmethod
    def assert_fail_if_entries_not_served(cls):
        """Mocket checks that all entries have been served at least once."""
        if not all(entry._served for entry in itertools.chain(*cls._entries.values())):
            raise AssertionError("Some Mocket entries have not been served")
