from .mocket import Mocketizer
from .utils import get_mocketize


async def wrapper(test, cls=Mocketizer, truesocket_recording_dir=None, *args, **kwargs):
    instance = args[0] if args else None
    namespace = None
    if truesocket_recording_dir:
        namespace = Mocketizer.get_namespace(test, instance)
    async with cls(
        instance,
        namespace=namespace,
        truesocket_recording_dir=truesocket_recording_dir,
    ):
        return await test(*args, **kwargs)


async_mocketize = get_mocketize(wrapper_=wrapper)


__all__ = ("async_mocketize",)
