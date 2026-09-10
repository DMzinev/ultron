"""Standard library unittest suite for real_coverage_repo fixture."""

import unittest
from math_ops import add, divide
from string_ops import shout, whisper


class TestOps(unittest.TestCase):
    def test_math(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(divide(10, 2), 5.0)

    def test_string(self):
        self.assertEqual(shout("hello"), "HELLO!")
        self.assertEqual(whisper("SECRET"), "secret...")


if __name__ == "__main__":
    unittest.main()
