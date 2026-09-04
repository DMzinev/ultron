import unittest
from ultron.core.adaptive_verifier import AdaptiveBoundaryVerifier, ddmin_shrink

class TestAdaptiveVerifier(unittest.TestCase):
    def test_ddmin_shrinks_failing_substring(self):
        # Target: any string containing "FAIL" triggers failure
        predicate = lambda s: "FAIL" in s
        initial_failing = "prefix_abc_123_FAIL_xyz_456_suffix"

        shrunk = ddmin_shrink(predicate, initial_failing)
        self.assertEqual(shrunk, "FAIL")

    def test_ddmin_shrinks_syntax_error_snippet(self):
        # Target: unclosed parenthesis
        predicate = lambda s: s.count("(") > s.count(")")
        initial_failing = "def foo():\n    x = (1 + 2\n    return x"

        shrunk = ddmin_shrink(predicate, initial_failing)
        self.assertTrue(predicate(shrunk))
        self.assertLess(len(shrunk), len(initial_failing))

    def test_generate_boundary_variants(self):
        variants = AdaptiveBoundaryVerifier.generate_boundary_variants("path")
        self.assertIn("", variants)
        self.assertIn(".", variants)
        self.assertTrue(any("nonexistent" in str(v) for v in variants))

if __name__ == "__main__":
    unittest.main()
