from mocket.mocketizer import Mocketizer
from mocket.utils import get_mocketize


async def wrapper(
    test,
    truesocket_recording_dir=None,
    strict_mode=False,
    strict_mode_allowed=None,
    skip_response_cache=False,
    *args,
    **kwargs,
):
    async with Mocketizer.factory(
        test,
        truesocket_recording_dir,
        strict_mode,
        strict_mode_allowed,
        skip_response_cache,
        args,
    ):
        return await test(*args, **kwargs)


async_mocketize = get_mocketize(wrapper_=wrapper)


__all__ = ("async_mocketize",)
