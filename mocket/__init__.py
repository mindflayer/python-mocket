try:
    # Py2
    from mocket import mocketize
except ImportError:
    # Py3
    from mocket.mocket import mocketize
