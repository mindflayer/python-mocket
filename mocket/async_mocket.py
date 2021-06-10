from mocket import Mocketizer, mocketize


def get_async_mocketize():
    class AsyncMocketizer(Mocketizer):
        async def __aenter__(*args, **kwargs):
            return Mocketizer.__enter__(*args, **kwargs)

        async def __aexit__(*args, **kwargs):
            return Mocketizer.__exit__(*args, **kwargs)

        @staticmethod
        def async_wrap(*args, **kwargs):
            return Mocketizer.wrap(*args, **kwargs)

    return mocketize(cls=AsyncMocketizer)


async_mocketize = get_async_mocketize()
