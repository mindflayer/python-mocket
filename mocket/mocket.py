"""Core Mocket singleton for socket mocking management."""

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
    """Singleton class managing all mock socket operations and entries."""

    _socket_pairs: ClassVar[dict[Address, tuple[int, int]]] = {}
    _address: ClassVar[Address | tuple[None, None]] = (None, None)
    _entries: ClassVar[dict[Address, list[MocketEntry]]] = collections.defaultdict(list)
    _requests: ClassVar[list] = []
    _record_storage: ClassVar[MocketRecordStorage | None] = None

    @classmethod
    def enable(
        cls,
        namespace: str | None = None,
        truesocket_recording_dir: str | None = None,
    ) -> None:
        """Enable Mocket socket mocking.

        Args:
            namespace: Namespace for recording storage (defaults to id of _entries)
            truesocket_recording_dir: Directory to store recorded requests/responses
        """
        if namespace is None:
            namespace = str(id(cls._entries))

        if truesocket_recording_dir is not None:
            recording_dir = Path(truesocket_recording_dir)

            assert recording_dir.is_dir(), f"Not a directory: {recording_dir}"

            cls._record_storage = MocketRecordStorage(
                directory=recording_dir,
                namespace=namespace,
            )

        mocket.inject.enable()

    @classmethod
    def disable(cls) -> None:
        """Disable Mocket socket mocking and clean up resources."""
        cls.reset()

        mocket.inject.disable()

    @classmethod
    def get_pair(cls, address: Address) -> tuple[int, int] | tuple[None, None]:
        """Get the file descriptor pair for a socket address.

        Given the id() of the caller, return a pair of file descriptors
        as a tuple of two integers: (<read_fd>, <write_fd>)

        Args:
            address: (host, port) tuple

        Returns:
            Tuple of (read_fd, write_fd) or (None, None) if not found
        """
        return cls._socket_pairs.get(address, (None, None))

    @classmethod
    def set_pair(cls, address: Address, pair: tuple[int, int]) -> None:
        """Store a file descriptor pair for a socket address.

        Store a pair of file descriptors under the key `address`
        as a tuple of two integers: (<read_fd>, <write_fd>)

        Args:
            address: (host, port) tuple
            pair: Tuple of (read_fd, write_fd)
        """
        cls._socket_pairs[address] = pair

    @classmethod
    def register(cls, *entries: MocketEntry) -> None:
        """Register mock entries with Mocket.

        Args:
            *entries: Variable number of MocketEntry instances to register
        """
        for entry in entries:
            cls._entries[entry.location].append(entry)

    @classmethod
    def get_entry(cls, host: str, port: int, data: Any) -> MocketEntry | None:
        """Get a matching entry for the given request data.

        Args:
            host: Hostname
            port: Port number
            data: Request data

        Returns:
            Matching MocketEntry or None
        """
        host = host or cls._address[0]
        port = port or cls._address[1]
        entries = cls._entries.get((host, port), [])
        for entry in entries:
            if entry.can_handle(data):
                return entry
        return None

    @classmethod
    def collect(cls, data: Any) -> None:
        """Collect a request in the list of all requests.

        Args:
            data: Request data to collect
        """
        cls._requests.append(data)

    @classmethod
    def reset(cls) -> None:
        """Reset all Mocket state and clean up file descriptors."""
        for r_fd, w_fd in cls._socket_pairs.values():
            os.close(r_fd)
            os.close(w_fd)
        cls._socket_pairs = {}
        cls._entries = collections.defaultdict(list)
        cls._requests = []
        cls._record_storage = None

    @classmethod
    def last_request(cls) -> Any:
        """Get the last request made.

        Returns:
            Last request data or None if no requests
        """
        if cls.has_requests():
            return cls._requests[-1]

    @classmethod
    def request_list(cls) -> list[Any]:
        """Get the list of all requests.

        Returns:
            List of all collected requests
        """
        return cls._requests

    @classmethod
    def remove_last_request(cls) -> None:
        """Remove the last request from the request list."""
        if cls.has_requests():
            del cls._requests[-1]

    @classmethod
    def has_requests(cls) -> bool:
        """Check if any requests have been made.

        Returns:
            True if there are requests, False otherwise
        """
        return bool(cls.request_list())

    @classmethod
    def get_namespace(cls) -> str | None:
        """Get the recording namespace.

        Returns:
            Namespace string or None if recording is not enabled
        """
        return cls._record_storage.namespace if cls._record_storage else None

    @classmethod
    def get_truesocket_recording_dir(cls) -> str | None:
        """Get the true socket recording directory.

        Returns:
            Directory path as string or None if recording is not enabled
        """
        return str(cls._record_storage.directory) if cls._record_storage else None

    @classmethod
    def assert_fail_if_entries_not_served(cls) -> None:
        """Assert that all registered entries have been served at least once.

        Raises:
            AssertionError: If any entries have not been served
        """
        if not all(entry._served for entry in itertools.chain(*cls._entries.values())):
            raise AssertionError("Some Mocket entries have not been served")
