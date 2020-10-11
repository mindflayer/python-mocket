try:
    # Py2
    from mocket import Mocket, MocketEntry, Mocketizer, mocketize
except ImportError:
    # Py3
    from mocket.mocket import Mocket, MocketEntry, Mocketizer, mocketize

__all__ = ("mocketize", "Mocket", "MocketEntry", "Mocketizer")

__version__ = "3.9.2"
