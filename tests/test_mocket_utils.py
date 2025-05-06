from typing import Callable
from unittest import TestCase
from unittest.mock import NonCallableMock, patch

import decorator

from mocket.utils import get_mocketize


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
