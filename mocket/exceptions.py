"""Mocket exception classes."""


class MocketException(Exception):
    """Base exception class for Mocket errors."""

    pass


class StrictMocketException(MocketException):
    """Exception raised when a socket operation is not allowed in STRICT mode."""

    pass
