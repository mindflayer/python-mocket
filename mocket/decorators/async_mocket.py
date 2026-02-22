"""Async version of Mocket decorator."""

from __future__ import annotations

from typing import Any, Callable

from mocket.decorators.mocketizer import Mocketizer
from mocket.utils import get_mocketize


async def wrapper(
    test: Callable,
    truesocket_recording_dir: str | None = None,
    strict_mode: bool = False,
    strict_mode_allowed: list | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Async wrapper function for @async_mocketize decorator.

    Args:
        test: Async test function to wrap
        truesocket_recording_dir: Directory for recording true socket calls
        strict_mode: Enable STRICT mode to forbid real socket calls
        strict_mode_allowed: List of allowed hosts in STRICT mode
        *args: Test arguments
        **kwargs: Test keyword arguments

    Returns:
        Result of the test function
    """
    async with Mocketizer.factory(
        test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args
    ):
        return await test(*args, **kwargs)


async_mocketize = get_mocketize(wrapper)


__all__ = ("async_mocketize",)
