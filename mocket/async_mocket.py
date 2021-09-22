from mocket import Mocketizer
from mocket.utils import get_mocketize


async def wrapper(test, cls=Mocketizer, truesocket_recording_dir=None, *args, **kwargs):
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
    async with cls(
        instance,
        namespace=namespace,
        truesocket_recording_dir=truesocket_recording_dir,
    ):
        return await test(*args, **kwargs)


async_mocketize = get_mocketize(wrapper_=wrapper)


__all__ = ("async_mocketize",)
