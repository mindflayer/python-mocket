"""Mocketizer decorator for managing Mocket lifecycle in tests."""

from __future__ import annotations

from typing import Any, Callable

from mocket.mocket import Mocket
from mocket.mode import MocketMode
from mocket.utils import get_mocketize


class Mocketizer:
    """Context manager and decorator for managing Mocket lifecycle in tests."""

    def __init__(
        self,
        instance: Any | None = None,
        namespace: str | None = None,
        truesocket_recording_dir: str | None = None,
        strict_mode: bool = False,
        strict_mode_allowed: list | None = None,
    ) -> None:
        """Initialize the Mocketizer.

        Args:
            instance: Test instance (optional)
            namespace: Namespace for recordings
            truesocket_recording_dir: Directory for recording true socket calls
            strict_mode: Enable STRICT mode to forbid real socket calls
            strict_mode_allowed: List of allowed hosts in STRICT mode
        """
        self.instance = instance
        self.truesocket_recording_dir = truesocket_recording_dir
        self.namespace = namespace or str(id(self))
        MocketMode.STRICT = strict_mode
        if strict_mode:
            MocketMode.STRICT_ALLOWED = strict_mode_allowed or []
        elif strict_mode_allowed:
            raise ValueError(
                "Allowed locations are only accepted when STRICT mode is active."
            )

    def enter(self) -> None:
        """Enter the Mocketizer context (enable Mocket)."""
        Mocket.enable(
            namespace=self.namespace,
            truesocket_recording_dir=self.truesocket_recording_dir,
        )
        if self.instance:
            self.check_and_call("mocketize_setup")

    def __enter__(self) -> Mocketizer:
        """Enter context manager.

        Returns:
            Self for use in `with` statements
        """
        self.enter()
        return self

    def exit(self) -> None:
        """Exit the Mocketizer context (disable Mocket)."""
        if self.instance:
            self.check_and_call("mocketize_teardown")

        Mocket.disable()

    def __exit__(self, type: Any, value: Any, tb: Any) -> None:
        """Exit context manager.

        Args:
            type: Exception type
            value: Exception value
            tb: Traceback
        """
        self.exit()

    async def __aenter__(self, *args: Any, **kwargs: Any) -> Mocketizer:
        """Enter async context manager.

        Returns:
            Self for use in `async with` statements
        """
        self.enter()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        """Exit async context manager.

        Args:
            *args: Exception arguments
            **kwargs: Exception keyword arguments
        """
        self.exit()

    def check_and_call(self, method_name: str) -> None:
        """Check if instance has a method and call it.

        Args:
            method_name: Name of method to check and call
        """
        method = getattr(self.instance, method_name, None)
        if callable(method):
            method()

    @staticmethod
    def factory(
        test: Callable,
        truesocket_recording_dir: str | None,
        strict_mode: bool,
        strict_mode_allowed: list | None,
        args: tuple,
    ) -> Mocketizer:
        """Create a Mocketizer instance for a test function.

        Args:
            test: Test function being decorated
            truesocket_recording_dir: Recording directory
            strict_mode: Enable STRICT mode
            strict_mode_allowed: Allowed hosts in STRICT mode
            args: Positional arguments to test

        Returns:
            Configured Mocketizer instance
        """
        instance = args[0] if args else None
        namespace = None
        if truesocket_recording_dir:
            namespace = ".".join(
                (
                    instance.__class__.__module__,
                    instance.__class__.__name__,
                    test.__name__,
                )
            )

        return Mocketizer(
            instance,
            namespace=namespace,
            truesocket_recording_dir=truesocket_recording_dir,
            strict_mode=strict_mode,
            strict_mode_allowed=strict_mode_allowed,
        )


def wrapper(
    test: Callable,
    truesocket_recording_dir: str | None = None,
    strict_mode: bool = False,
    strict_mode_allowed: list | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Wrapper function for @mocketize decorator.

    Args:
        test: Test function to wrap
        truesocket_recording_dir: Recording directory
        strict_mode: Enable STRICT mode
        strict_mode_allowed: Allowed hosts in STRICT mode
        *args: Test arguments
        **kwargs: Test keyword arguments

    Returns:
        Result of the test function
    """
    with Mocketizer.factory(
        test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args
    ):
        return test(*args, **kwargs)


mocketize = get_mocketize(wrapper)
