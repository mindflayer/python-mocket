from __future__ import annotations

import functools
import inspect

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
        MocketMode().STRICT = strict_mode
        if strict_mode:
            MocketMode().STRICT_ALLOWED = strict_mode_allowed or []
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
        if truesocket_recording_dir and instance:
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


def _function_wrapper(
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


_function_mocketize = get_mocketize(_function_wrapper)


def _class_decorator_factory(**options):
    def decorator(cls):
        orig_setup = getattr(cls, "setUp", lambda self, *a, **kw: None)
        orig_td = getattr(cls, "tearDown", lambda self, *a, **kw: None)
        use_add_cleanup = hasattr(cls, "addCleanup")

        def setUp(self, *a, **kw):
            ctx = Mocketizer(instance=self, **options)
            ctx.enter()
            if use_add_cleanup:
                self.addCleanup(ctx.exit)
            else:
                self.__mocket_ctx = ctx
            orig_setup(self, *a, **kw)

        cls.setUp = functools.wraps(orig_setup)(setUp)

        if not use_add_cleanup:

            def tearDown(self, *a, **kw):
                try:
                    orig_td(self, *a, **kw)
                finally:
                    if hasattr(self, "__mocket_ctx"):
                        self.__mocket_ctx.exit()

            cls.tearDown = functools.wraps(orig_td)(tearDown)

        return cls

    return decorator


def mocketize(*dargs, **dkwargs):
    # bare @mocketize
    if dargs and len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
        target = dargs[0]
        if inspect.isclass(target):
            return _class_decorator_factory()(target)
        return _function_mocketize(target)

    # @mocketize(...)
    def real_decorator(target):
        if inspect.isclass(target):
            return _class_decorator_factory(**dkwargs)(target)
        return _function_mocketize(**dkwargs)(target)

    return real_decorator
