import contextlib

from mocket import MocketSSLContext

with contextlib.suppress(ModuleNotFoundError):
    from aiohttp import ClientRequest
    from aiohttp.connector import TCPConnector

    class MocketTCPConnector(TCPConnector):
        """
        `aiohttp` reuses SSLContext instances created at import-time,
        making it more difficult for Mocket to do its job.
        This is an attempt to make things smoother, at the cost of
        slightly patching the `ClientSession` while testing.
        """

        def _get_ssl_context(self, req: ClientRequest) -> MocketSSLContext:
            return MocketSSLContext()
