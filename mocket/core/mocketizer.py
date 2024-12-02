from __future__ import annotations

from types import TracebackType
from typing import Any

from typing_extensions import Self

from mocket.core.mocket import Mocket
from mocket.core.mode import MocketMode
from mocket.core.types import Address, AnyCallable
from mocket.core.utils import get_mocketize


class Mocketizer:
    def __init__(
        self,
        instance: Any | None = None,
        namespace: str | None = None,
        truesocket_recording_dir: str | None = None,
        strict_mode: bool = False,
        strict_mode_allowed: list[str | Address] | None = None,
    ):
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
        Mocket.enable(
            namespace=self.namespace,
            truesocket_recording_dir=self.truesocket_recording_dir,
        )
        if self.instance:
            self.check_and_call("mocketize_setup")

    def __enter__(self) -> Self:
        self.enter()
        return self

    def exit(self) -> None:
        if self.instance:
            self.check_and_call("mocketize_teardown")

        Mocket.disable()

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exit()

    async def __aenter__(self) -> Self:
        self.enter()
        return self

    async def __aexit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exit()

    def check_and_call(self, method_name: str) -> None:
        method = getattr(self.instance, method_name, None)
        if callable(method):
            method()

    @staticmethod
    def factory(
        test: AnyCallable,
        truesocket_recording_dir: str | None,
        strict_mode: bool,
        strict_mode_allowed: list[str | Address] | None,
        args: Any,
    ) -> Mocketizer:
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
    test: AnyCallable,
    truesocket_recording_dir: str | None = None,
    strict_mode: bool = False,
    strict_mode_allowed: list[str | Address] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    with Mocketizer.factory(
        test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args
    ):
        return test(*args, **kwargs)


mocketize = get_mocketize(wrapper_=wrapper)
