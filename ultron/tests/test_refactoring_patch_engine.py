"""
ultron.tests.test_refactoring_patch_engine
Unit test suite asserting AST refactoring patch generation, unified diff formatting, and validation.
"""

import unittest
from ultron.core.refactoring_patch_engine import RefactoringPatchEngine, norm_path


class TestRefactoringPatchEngine(unittest.TestCase):
    """Unit tests for deterministic RefactoringPatchEngine."""

    def test_norm_path(self):
        """Asserts path normalization to POSIX format."""
        self.assertEqual(norm_path("ultron\\core\\analyzer.py"), "ultron/core/analyzer.py")
        self.assertEqual(norm_path(None), "")

    def test_validate_patch_syntax(self):
        """Asserts AST syntax validator detects valid vs invalid code."""
        self.assertTrue(RefactoringPatchEngine.validate_patch_syntax("def foo():\n    return 42\n"))
        self.assertFalse(RefactoringPatchEngine.validate_patch_syntax("def foo(\n    syntax error"))
        self.assertFalse(RefactoringPatchEngine.validate_patch_syntax(""))

    def test_format_unified_diff(self):
        """Asserts unified diff formatting compliance."""
        orig = ["line 1", "line 2", "line 3"]
        mod = ["line 1", "line 2 modified", "line 3"]
        diff = RefactoringPatchEngine.format_unified_diff(orig, mod, "module.py")
        self.assertIn("--- a/module.py", diff)
        self.assertIn("+++ b/module.py", diff)
        self.assertIn("-line 2", diff)
        self.assertIn("+line 2 modified", diff)

    def test_generate_function_extraction_patch_success(self):
        """Asserts patch generation produces valid AST diff and complexity reduction."""
        sample_code = (
            "def monolithic_calculator(x, y, op):\n"
            "    if op == 'add':\n"
            "        return x + y\n"
            "    elif op == 'sub':\n"
            "        return x - y\n"
            "    elif op == 'mul':\n"
            "        return x * y\n"
            "    elif op == 'div':\n"
            "        if y != 0:\n"
            "            return x / y\n"
            "        return None\n"
            "    return 0\n"
        )
        res = RefactoringPatchEngine.generate_function_extraction_patch("math_ops.py", sample_code)
        self.assertTrue(res["success"])
        self.assertEqual(res["target_function"], "monolithic_calculator")
        self.assertIn("--- a/math_ops.py", res["diff"])
        self.assertIn("+++ b/math_ops.py", res["diff"])
        self.assertGreater(res["complexity_before"], 1.0)
        self.assertIn("engine_version", res["provenance"])

    def test_generate_patch_empty_or_no_functions(self):
        """Asserts empty code or files without functions return clean failure."""
        empty_res = RefactoringPatchEngine.generate_function_extraction_patch("empty.py", "")
        self.assertFalse(empty_res["success"])
        self.assertIn("empty", empty_res["error"].lower())

        no_funcs_res = RefactoringPatchEngine.generate_function_extraction_patch("constants.py", "X = 1\nY = 2\n")
        self.assertFalse(no_funcs_res["success"])
        self.assertIn("no function", no_funcs_res["error"].lower())

    def test_generate_patch_syntax_error(self):
        """Asserts corrupted source code returns syntax error report."""
        bad_res = RefactoringPatchEngine.generate_function_extraction_patch("bad.py", "def broken(\n  incomplete")
        self.assertFalse(bad_res["success"])
        self.assertIn("syntax error", bad_res["error"].lower())


if __name__ == "__main__":
    unittest.main()
