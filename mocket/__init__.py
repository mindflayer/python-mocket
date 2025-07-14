import importlib
import sys

from mocket.decorators.async_mocket import async_mocketize
from mocket.decorators.mocketizer import Mocketizer, mocketize
from mocket.entry import MocketEntry
from mocket.mocket import Mocket
from mocket.ssl.context import MocketSSLContext

# NOTE the following lines are here for backwards-compatibility,
# to keep old import-paths working
from mocket.ssl.context import MocketSSLContext as FakeSSLContext

sys.modules["mocket.mockhttp"] = importlib.import_module("mocket.mocks.mockhttp")
sys.modules["mocket.mockredis"] = importlib.import_module("mocket.mocks.mockredis")
sys.modules["mocket.async_mocket"] = importlib.import_module(
    "mocket.decorators.async_mocket"
)
sys.modules["mocket.mocketizer"] = importlib.import_module(
    "mocket.decorators.mocketizer"
)


__all__ = (
    "async_mocketize",
    "mocketize",
    "Mocket",
    "MocketEntry",
    "Mocketizer",
    "MocketSSLContext",
    "FakeSSLContext",
)

__version__ = "3.13.10"
