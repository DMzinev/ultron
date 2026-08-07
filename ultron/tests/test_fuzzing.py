"""
Ultron Adversarial Fuzzing & Chaos Test Suite
Campaign 13 & Wave 6: Defensive Input Hardening & Zero Unhandled Tracebacks
"""

import unittest
import json
import os
import sys
from unittest.mock import MagicMock

from ultron.interfaces.server import UltronAPIHandler

class TestAdversarialFuzzing(unittest.TestCase):
    def setUp(self):
        self.handler = UltronAPIHandler.__new__(UltronAPIHandler)
        self.handler.send_json_response = MagicMock()
        self.handler.get_request_data = MagicMock()

    def test_fuzz_analyze_null_payload(self):
        """Fuzz /api/v1/analyze with null payload."""
        from ultron.interfaces.api.routes.analysis_routes import handle_v1_analyze
        self.handler.get_request_data.return_value = None
        handle_v1_analyze(self.handler)
        self.handler.send_json_response.assert_called_once_with(400, None, "Invalid or corrupted JSON body")

    def test_fuzz_analyze_empty_path(self):
        """Fuzz /api/v1/analyze with empty path string."""
        from ultron.interfaces.api.routes.analysis_routes import handle_v1_analyze
        self.handler.get_request_data.return_value = {"repo": ""}
        handle_v1_analyze(self.handler)
        self.handler.send_json_response.assert_called_once_with(400, None, "Repository path string must not be empty.")

    def test_fuzz_analyze_non_existent_path(self):
        """Fuzz /api/v1/analyze with non-existent directory path."""
        from ultron.interfaces.api.routes.analysis_routes import handle_v1_analyze
        fake_path = os.path.normpath("C:/fake/does/not/exist")
        self.handler.get_request_data.return_value = {"repo": fake_path}
        handle_v1_analyze(self.handler)
        self.assertTrue(self.handler.send_json_response.called)
        status = self.handler.send_json_response.call_args[0][0]
        self.assertEqual(status, 400)

    def test_fuzz_export_brief_invalid_format(self):
        """Fuzz /api/v1/export-brief with unsupported format string."""
        from ultron.interfaces.api.routes.export_routes import handle_v1_export_brief
        self.handler.get_request_data.return_value = {"repo": ".", "format": "exe_invalid"}
        handle_v1_export_brief(self.handler)
        self.assertTrue(self.handler.send_json_response.called)
        status = self.handler.send_json_response.call_args[0][0]
        self.assertEqual(status, 400)

if __name__ == "__main__":
    unittest.main()
