try:
    # Py2
    from mocket import mocketize, Mocket, MocketEntry
except ImportError:
    # Py3
    from mocket.mocket import mocketize, Mocket, MocketEntry

__all__ = (mocketize, Mocket, MocketEntry)
