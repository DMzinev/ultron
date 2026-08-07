"""
Ultron Fault Injection & Chaos Engineering Test Suite
Campaign 13 & Wave 6: Path-Filtered Mock Side-Effects & Diagnostics Key Assertions
"""

import unittest
import os
import sys
import sqlite3
from unittest.mock import patch, MagicMock

from ultron.core.telemetry.errors import ErrorDiagnostics, ErrorCategory
from ultron.interfaces.api.routes.analysis_routes import handle_v1_analyze
from ultron.interfaces.api.routes.export_routes import handle_v1_export_brief

class TestFaultInjection(unittest.TestCase):
    def setUp(self):
        self.handler = MagicMock()
        self.handler.headers = {}
        self.handler.send_json_response = MagicMock()

    def test_fault_injection_invalid_json(self):
        """Fault Injection: Invalid JSON body returned by get_request_data."""
        self.handler.get_request_data.return_value = None
        handle_v1_analyze(self.handler)

        self.handler.send_json_response.assert_called_once()
        status_code = self.handler.send_json_response.call_args[0][0]
        self.assertEqual(status_code, 400)

    def test_fault_injection_sqlite_locked(self):
        """Fault Injection: SQLite Database locked error simulation."""
        with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("database is locked")):
            from ultron.core.rkm.store import RepositoryStore
            with self.assertRaises(sqlite3.OperationalError):
                RepositoryStore(":memory:")

    def test_fault_injection_path_filtered_open_error(self):
        """Fault Injection: Path-filtered FileNotFoundError simulation on target files."""
        orig_open = open

        def conditional_open(file, *args, **kwargs):
            if isinstance(file, (str, bytes)) and "non_existent_chaos_target" in str(file):
                raise FileNotFoundError("Chaos target file missing")
            return orig_open(file, *args, **kwargs)

        with patch("builtins.open", side_effect=conditional_open):
            env = ErrorDiagnostics.format_error_envelope(
                "Chaos target file missing",
                FileNotFoundError("Chaos target file missing"),
                operation="Chaos File Read"
            )
            self.assertEqual(env["diagnostics"]["category"], ErrorCategory.FILE_SYSTEM_ERROR)
            self.assertEqual(env["diagnostics"]["operation"], "Chaos File Read")
            self.assertIn("recovery_suggestion", env["diagnostics"])

if __name__ == "__main__":
    unittest.main()
