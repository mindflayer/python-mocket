from typing import Callable
from unittest import TestCase
from unittest.mock import NonCallableMock, patch

import decorator

from mocket.utils import get_mocketize, hexdump, hexload


def mock_decorator(func: Callable[[], None]) -> None:
    return func()


class GetMocketizeTestCase(TestCase):
    @patch.object(decorator, "decorator")
    def test_get_mocketize_with_kwsyntax(self, dec: NonCallableMock) -> None:
        get_mocketize(mock_decorator)
        dec.assert_called_once_with(mock_decorator, kwsyntax=True)

    @patch.object(decorator, "decorator")
    def test_get_mocketize_without_kwsyntax(self, dec: NonCallableMock) -> None:
        dec.side_effect = [
            TypeError("kwsyntax is not supported in this version of decorator"),
            mock_decorator,
        ]

        get_mocketize(mock_decorator)
        # First time called with kwsyntax=True, which failed with TypeError
        dec.call_args_list[0].assert_compare_to((mock_decorator,), {"kwsyntax": True})
        # Second time without kwsyntax, which succeeds
        dec.call_args_list[1].assert_compare_to((mock_decorator,))


class HexdumpTestCase(TestCase):
    def test_hexdump_converts_bytes_to_spaced_hex(self) -> None:
        assert hexdump(b"Hi") == "48 69"

    def test_hexdump_empty_bytes(self) -> None:
        assert hexdump(b"") == ""

    def test_hexdump_roundtrip_with_hexload(self) -> None:
        data = b"bar foobar foo"
        assert hexload(hexdump(data)) == data


class HexloadTestCase(TestCase):
    def test_hexload_converts_spaced_hex_to_bytes(self) -> None:
        assert hexload("48 69") == b"Hi"

    def test_hexload_empty_string(self) -> None:
        assert hexload("") == b""

    def test_hexload_invalid_hex_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            hexload("ZZ ZZ")
