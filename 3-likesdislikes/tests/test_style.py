"""Код-стайл: тело любой функции или метода не длиннее 5 строк."""
import sys
import unittest

from tests.support import ROOT

sys.path.insert(0, str(ROOT / "tools"))
from method_length import check  # noqa: E402


class StyleTest(unittest.TestCase):
    def test_methods_are_short(self) -> None:
        self.assertEqual(check([ROOT]), [])


if __name__ == "__main__":
    unittest.main()
