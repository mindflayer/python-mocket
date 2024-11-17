from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from mocket.exceptions import StrictMocketException
from mocket.mocket import Mocket

if TYPE_CHECKING:  # pragma: no cover
    from typing import NoReturn


class MocketMode:
    __shared_state: ClassVar[dict[str, Any]] = {}
    STRICT: ClassVar = None
    STRICT_ALLOWED: ClassVar = None

    def __init__(self) -> None:
        self.__dict__ = self.__shared_state

    def is_allowed(self, location: str | tuple[str, int]) -> bool:
        """
        Checks if (`host`, `port`) or at least `host`
        are allowed locations to perform real `socket` calls
        """
        if not self.STRICT:
            return True

        host_allowed = False
        if isinstance(location, tuple):
            host_allowed = location[0] in self.STRICT_ALLOWED
        return host_allowed or location in self.STRICT_ALLOWED

    @staticmethod
    def raise_not_allowed() -> NoReturn:
        current_entries = [
            (location, "\n    ".join(map(str, entries)))
            for location, entries in Mocket._entries.items()
        ]
        formatted_entries = "\n".join(
            [f"  {location}:\n    {entries}" for location, entries in current_entries]
        )
        raise StrictMocketException(
            "Mocket tried to use the real `socket` module while STRICT mode was active.\n"
            f"Registered entries:\n{formatted_entries}"
        )
