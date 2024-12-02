from __future__ import annotations

from typing import Any

from mocket.core.mocketizer import Mocketizer
from mocket.core.types import Address, AnyCallable
from mocket.core.utils import get_mocketize


async def wrapper(
    test: AnyCallable,
    truesocket_recording_dir: str | None = None,
    strict_mode: bool = False,
    strict_mode_allowed: list[str | Address] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    async with Mocketizer.factory(
        test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args
    ):
        return await test(*args, **kwargs)


async_mocketize = get_mocketize(wrapper_=wrapper)
