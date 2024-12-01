from __future__ import annotations

from typing import Any, Dict, Tuple, Union

from typing_extensions import Buffer, TypeAlias

Address = Tuple[str, int]

# adapted from typeshed/stdlib/_typeshed/__init__.pyi
WriteableBuffer: TypeAlias = Buffer
ReadableBuffer: TypeAlias = Buffer

# from typeshed/stdlib/_socket.pyi
_Address: TypeAlias = Union[Tuple[Any, ...], str, ReadableBuffer]
_RetAddress: TypeAlias = Any

# from typeshed/stdlib/ssl.pyi
_PCTRTT: TypeAlias = Tuple[Tuple[str, str], ...]
_PCTRTTT: TypeAlias = Tuple[_PCTRTT, ...]
_PeerCertRetDictType: TypeAlias = Dict[str, Union[str, _PCTRTTT, _PCTRTT]]
