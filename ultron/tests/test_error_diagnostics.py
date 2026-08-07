"""
Ultron Unit Tests for Error Intelligence & Diagnostics Engine
"""
import unittest
from ultron.core.telemetry.errors import ErrorDiagnostics, ErrorCategory

class TestErrorDiagnostics(unittest.TestCase):
    def test_classify_syntax_error(self):
        err = SyntaxError("invalid syntax")
        cat = ErrorDiagnostics.classify_exception(err)
        self.assertEqual(cat, ErrorCategory.SYNTAX_ERROR)

    def test_format_error_envelope_backward_compatibility(self):
        env = ErrorDiagnostics.format_error_envelope("File not found", FileNotFoundError(), "File Read")
        self.assertIn("error", env)
        self.assertEqual(env["error"], "File not found")
        self.assertIn("diagnostics", env)
        self.assertEqual(env["diagnostics"]["category"], ErrorCategory.FILE_SYSTEM_ERROR)
        self.assertIn("recovery_suggestion", env["diagnostics"])

if __name__ == "__main__":
    unittest.main()
