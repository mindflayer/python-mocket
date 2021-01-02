import decorator

from mocket import Mocketizer


def get_async_mocketize():
    class AsyncMocketizer(Mocketizer):
        async def __aenter__(*args, **kwargs):
            return Mocketizer.__enter__(*args, **kwargs)

        async def __aexit__(*args, **kwargs):
            return Mocketizer.__exit__(*args, **kwargs)

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
