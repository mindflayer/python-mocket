from __future__ import annotations

import contextlib
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from mocket.compat import decode_from_bytes, encode_to_bytes
from mocket.types import Address
from mocket.utils import hexdump, hexload

hash_function = hashlib.md5

with contextlib.suppress(ImportError):
    from xxhash_cffi import xxh32 as xxhash_cffi_xxh32

    hash_function = xxhash_cffi_xxh32

with contextlib.suppress(ImportError):
    from xxhash import xxh32 as xxhash_xxh32

    hash_function = xxhash_xxh32


def _hash_prepare_request(data: bytes) -> bytes:
    _data = decode_from_bytes(data)
    return encode_to_bytes("".join(sorted(_data.split("\r\n"))))


def _hash_request(data: bytes) -> str:
    _data = _hash_prepare_request(data)
    return hash_function(_data).hexdigest()


def _hash_request_fallback(data: bytes) -> str:
    _data = _hash_prepare_request(data)
    return hashlib.md5(_data).hexdigest()


@dataclass
class MocketRecord:
    host: str
    port: int
    request: bytes
    response: bytes


class MocketRecordStorage:
    def __init__(self, directory: Path, namespace: str) -> None:
        self._directory = directory
        self._namespace = namespace
        self._records: defaultdict[Address, defaultdict[str, MocketRecord]] = (
            defaultdict(defaultdict)
        )

        self._load()

    @property
    def directory(self) -> Path:
        return self._directory

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def file(self) -> Path:
        return self._directory / f"{self._namespace}.json"

    def _load(self) -> None:
        if not self.file.exists():
            return

        json_data = self.file.read_text()
        records = json.loads(json_data)
        for host, port_signature_record in records.items():
            for port, signature_record in port_signature_record.items():
                for signature, record in signature_record.items():
                    # NOTE backward-compat
                    try:
                        request_data = hexload(record["request"])
                    except ValueError:
                        request_data = record["request"]

                    self._records[(host, int(port))][signature] = MocketRecord(
                        host=host,
                        port=port,
                        request=request_data,
                        response=hexload(record["response"]),
                    )

    def _save(self) -> None:
        data: dict[str, dict[str, dict[str, dict[str, str]]]] = defaultdict(
            lambda: defaultdict(defaultdict)
        )
        for address, signature_record in self._records.items():
            host, port = address
            for signature, record in signature_record.items():
                data[host][str(port)][signature] = dict(
                    request=decode_from_bytes(record.request),
                    response=hexdump(record.response),
                )

        json_data = json.dumps(data, indent=4, sort_keys=True)
        self.file.parent.mkdir(exist_ok=True)
        self.file.write_text(json_data)

    def get_records(self, address: Address) -> list[MocketRecord]:
        return list(self._records[address].values())

    def get_record(self, address: Address, request: bytes) -> MocketRecord | None:
        # NOTE for backward-compat
        request_signature_fallback = _hash_request_fallback(request)
        if request_signature_fallback in self._records[address]:
            return self._records[address].get(request_signature_fallback)

        request_signature = _hash_request(request)
        if request_signature in self._records[address]:
            return self._records[address][request_signature]

        return None

    def put_record(
        self,
        address: Address,
        request: bytes,
        response: bytes,
    ) -> None:
        host, port = address
        record = MocketRecord(
            host=host,
            port=port,
            request=request,
            response=response,
        )

        # NOTE for backward-compat
        request_signature_fallback = _hash_request_fallback(request)
        if request_signature_fallback in self._records[address]:
            self._records[address][request_signature_fallback] = record
            return

        request_signature = _hash_request(request)
        self._records[address][request_signature] = record
        self._save()
