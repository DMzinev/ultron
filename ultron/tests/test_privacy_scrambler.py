"""
ultron.tests.test_privacy_scrambler
Unit test suite asserting HMAC-SHA256 privacy tokenization and deterministic bidirectional recovery.
"""

import unittest
from ultron.core.privacy_scrambler import PrivacyScrambler


class TestPrivacyScrambler(unittest.TestCase):
    """Unit tests for PrivacyScrambler."""

    def test_scramble_and_unscramble_roundtrip(self):
        """Asserts scrambled code context can be restored identically via mapping."""
        code = (
            "class PaymentProcessor:\n"
            "    def execute_transaction(self, amount):\n"
            "        return amount * 1.05\n"
        )
        file_path = "src/payments/processor.py"
        scrambled, mapping = PrivacyScrambler.scramble_code_context(code, file_path)

        self.assertNotIn("PaymentProcessor", scrambled)
        self.assertNotIn("execute_transaction", scrambled)
        self.assertIn("$SYM_", scrambled)

        recovered = PrivacyScrambler.unscramble_text(scrambled, mapping)
        self.assertEqual(recovered, code)

    def test_deterministic_salted_tokens(self):
        """Asserts identical salt and tokens produce identical hash tokens."""
        t1 = PrivacyScrambler._hash_token("AuthService", "SYM", "salt123")
        t2 = PrivacyScrambler._hash_token("AuthService", "SYM", "salt123")
        t3 = PrivacyScrambler._hash_token("AuthService", "SYM", "different_salt")

        self.assertEqual(t1, t2)
        self.assertNotEqual(t1, t3)

    def test_prefix_collision_safety(self):
        """Asserts descending-length token substitution prevents prefix collisions."""
        mapping = {
            "$SYM_a": "compute",
            "$SYM_b": "compute_total_metrics"
        }
        scrambled = "def $SYM_b(): return $SYM_a()"
        unscrambled = PrivacyScrambler.unscramble_text(scrambled, mapping)

        self.assertEqual(unscrambled, "def compute_total_metrics(): return compute()")

    def test_path_scrambling(self):
        """Asserts file path is anonymized into $PATH_ token."""
        code = "from internal.billing.engine import Bill"
        path = "internal/billing/engine.py"
        scrambled, mapping = PrivacyScrambler.scramble_code_context(code, path)

        path_tokens = [k for k in mapping.keys() if k.startswith("$PATH_")]
        self.assertEqual(len(path_tokens), 1)
        self.assertEqual(mapping[path_tokens[0]], path)

    def test_empty_input_handling(self):
        """Asserts empty code text returns empty string without error."""
        scrambled, mapping = PrivacyScrambler.scramble_code_context("", "")
        self.assertEqual(scrambled, "")
        self.assertIsInstance(mapping, dict)

    def test_unscramble_empty_mapping(self):
        """Asserts unscrambling with empty mapping returns input text."""
        text = "Hello world"
        res = PrivacyScrambler.unscramble_text(text, {})
        self.assertEqual(res, text)


if __name__ == "__main__":
    unittest.main()
