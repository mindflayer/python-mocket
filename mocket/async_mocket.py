from sys import version_info

import decorator

from mocket import Mocket, Mocketizer


def get_async_mocketize():
    major, minor = version_info[:2]
    if major == 3 and minor >= 5:

        class AsyncMocketizer(Mocketizer):
            async def __aenter__(self):
                Mocket.enable(
                    namespace=self.namespace,
                    truesocket_recording_dir=self.truesocket_recording_dir,
                )
                if self.instance:
                    self.check_and_call("mocketize_setup")

            async def __aexit__(self, type, value, tb):
                if self.instance:
                    self.check_and_call("mocketize_teardown")
                Mocket.disable()

            @staticmethod
            def async_wrap(test=None, truesocket_recording_dir=None):
                async def wrapper(t, *args, **kw):
                    instance = args[0] if args else None
                    namespace = ".".join(
                        (
                            instance.__class__.__module__,
                            instance.__class__.__name__,
                            t.__name__,
                        )
                    )
                    async with AsyncMocketizer(
                        instance,
                        namespace=namespace,
                        truesocket_recording_dir=truesocket_recording_dir,
                    ):
                        await t(*args, **kw)
                    return wrapper

                return decorator.decorator(wrapper, test)

        return AsyncMocketizer.async_wrap


async_mocketize = get_async_mocketize()
