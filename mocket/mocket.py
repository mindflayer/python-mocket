from __future__ import annotations

import collections
import itertools
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import mocket.inject
from mocket.recording import MocketRecordStorage

# NOTE this is here for backwards-compat to keep old import-paths working
# from mocket.socket import MocketSocket as MocketSocket

if TYPE_CHECKING:
    from mocket.entry import MocketEntry
    from mocket.types import Address


class Mocket:
    _socket_pairs: ClassVar[dict[Address, tuple[int, int]]] = {}
    _address: ClassVar[Address] = (None, None)
    _entries: ClassVar[dict[Address, list[MocketEntry]]] = collections.defaultdict(list)
    _requests: ClassVar[list] = []
    _record_storage: ClassVar[MocketRecordStorage | None] = None

    @classmethod
    def enable(
        cls,
        namespace: str | None = None,
        truesocket_recording_dir: str | None = None,
    ) -> None:
        if namespace is None:
            namespace = str(id(cls._entries))

        if truesocket_recording_dir is not None:
            recording_dir = Path(truesocket_recording_dir)

            if not recording_dir.is_dir():
                # JSON dumps will be saved here
                raise AssertionError

            cls._record_storage = MocketRecordStorage(
                directory=recording_dir,
                namespace=namespace,
            )

        mocket.inject.enable()

    @classmethod
    def disable(cls) -> None:
        cls.reset()

        mocket.inject.disable()

    @classmethod
    def get_pair(cls, address: Address) -> tuple[int, int] | tuple[None, None]:
        """
        Given the id() of the caller, return a pair of file descriptors
        as a tuple of two integers: (<read_fd>, <write_fd>)
        """
        return cls._socket_pairs.get(address, (None, None))

    @classmethod
    def set_pair(cls, address: Address, pair: tuple[int, int]) -> None:
        """
        Store a pair of file descriptors under the key `id_`
        as a tuple of two integers: (<read_fd>, <write_fd>)
        """
        cls._socket_pairs[address] = pair

    @classmethod
    def register(cls, *entries: MocketEntry) -> None:
        for entry in entries:
            cls._entries[entry.location].append(entry)

    @classmethod
    def get_entry(cls, host: str, port: int, data) -> MocketEntry | None:
        host = host or cls._address[0]
        port = port or cls._address[1]
        entries = cls._entries.get((host, port), [])
        for entry in entries:
            if entry.can_handle(data):
                return entry
        return None

    @classmethod
    def collect(cls, data) -> None:
        cls._requests.append(data)

    @classmethod
    def reset(cls) -> None:
        for r_fd, w_fd in cls._socket_pairs.values():
            os.close(r_fd)
            os.close(w_fd)
        cls._socket_pairs = {}
        cls._entries = collections.defaultdict(list)
        cls._requests = []
        cls._record_storage = None

    @classmethod
    def last_request(cls) -> Any:
        if cls.has_requests():
            return cls._requests[-1]

    @classmethod
    def request_list(cls) -> list[Any]:
        return cls._requests

    @classmethod
    def remove_last_request(cls) -> None:
        if cls.has_requests():
            del cls._requests[-1]

    @classmethod
    def has_requests(cls) -> bool:
        return bool(cls.request_list())

    @classmethod
    def get_namespace(cls) -> str | None:
        if not cls._record_storage:
            return None
        return cls._record_storage.namespace

    @classmethod
    def get_truesocket_recording_dir(cls) -> str | None:
        if not cls._record_storage:
            return None
        return str(cls._record_storage.directory)

    @classmethod
    def assert_fail_if_entries_not_served(cls) -> None:
        """Mocket checks that all entries have been served at least once."""
        if not all(entry._served for entry in itertools.chain(*cls._entries.values())):
            raise AssertionError("Some Mocket entries have not been served")
