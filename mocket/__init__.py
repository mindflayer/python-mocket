try:
    # Py2
    from mocket import mocketize, Mocket, MocketEntry, Mocketizer
except ImportError:
    # Py3
    from mocket.mocket import mocketize, Mocket, MocketEntry, Mocketizer

__all__ = (mocketize, Mocket, MocketEntry, Mocketizer)

__version__ = '2.7.2'
