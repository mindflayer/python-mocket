from mocket.mocket import Mocket
from mocket.mode import MocketMode
from mocket.utils import get_mocketize


class Mocketizer:
    def __init__(
        self,
        instance=None,
        namespace=None,
        truesocket_recording_dir=None,
        strict_mode=False,
        strict_mode_allowed=None,
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

    def enter(self):
        Mocket.enable(
            namespace=self.namespace,
            truesocket_recording_dir=self.truesocket_recording_dir,
        )
        if self.instance:
            self.check_and_call("mocketize_setup")

    def __enter__(self):
        self.enter()
        return self

    def exit(self):
        if self.instance:
            self.check_and_call("mocketize_teardown")

        Mocket.disable()

    def __exit__(self, type, value, tb):
        self.exit()

    async def __aenter__(self, *args, **kwargs):
        self.enter()
        return self

    async def __aexit__(self, *args, **kwargs):
        self.exit()

    def check_and_call(self, method_name):
        method = getattr(self.instance, method_name, None)
        if callable(method):
            method()

    @staticmethod
    def factory(test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args):
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
    test,
    truesocket_recording_dir=None,
    strict_mode=False,
    strict_mode_allowed=None,
    *args,
    **kwargs,
):
    with Mocketizer.factory(
        test, truesocket_recording_dir, strict_mode, strict_mode_allowed, args
    ):
        return test(*args, **kwargs)


mocketize = get_mocketize(wrapper)
