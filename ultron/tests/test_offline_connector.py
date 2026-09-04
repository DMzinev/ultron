"""
ultron.tests.test_offline_connector
Unit test suite asserting offline LLM connectivity probing and deterministic fallback synthesis.
"""

import unittest
from ultron.core.ai.offline_connector import OfflineLLMConnector


class TestOfflineLLMConnector(unittest.TestCase):
    """Unit tests for OfflineLLMConnector."""

    def test_probe_connectivity_offline(self):
        """Asserts probing on unreachable loopback ports returns structured offline dict."""
        dead_endpoints = {
            "test_dead_service": "http://127.0.0.1:59999"
        }
        res = OfflineLLMConnector.probe_connectivity(endpoints=dead_endpoints)
        self.assertIsInstance(res, dict)
        self.assertFalse(res["available"])
        self.assertIn("test_dead_service", res["endpoints"])
        self.assertFalse(res["endpoints"]["test_dead_service"])

    def test_build_prompt(self):
        """Asserts constructed prompt includes file path, issue, and code context."""
        prompt = OfflineLLMConnector._build_prompt(
            file_path="src\\core\\engine.py",
            code_snippet="def run(): pass",
            architectural_issue="Cyclomatic complexity 18"
        )
        self.assertIn("src/core/engine.py", prompt)
        self.assertIn("Cyclomatic complexity 18", prompt)
        self.assertIn("def run(): pass", prompt)

    def test_generate_refactoring_plan_fallback(self):
        """Asserts fallback AST plan generates valid structured output when daemons are offline."""
        res = OfflineLLMConnector.generate_refactoring_plan(
            file_path="ultron/core/hub.py",
            code_snippet="class Hub: pass",
            architectural_issue="High coupling score",
            endpoint="http://127.0.0.1:59999"  # Deliberately dead port to force fallback
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["file"], "ultron/core/hub.py")
        self.assertIn("Ultron Deterministic AST Synthesis", res["source"])
        self.assertIn("Architectural Refactoring Plan", res["plan"])

    def test_generate_refactoring_plan_empty_snippet(self):
        """Asserts graceful handling when code snippet is empty."""
        res = OfflineLLMConnector.generate_refactoring_plan(
            file_path="empty.py",
            code_snippet="",
            architectural_issue="Missing definitions"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["file"], "empty.py")

    def test_path_normalization_in_prompt(self):
        """Asserts Windows path backslashes are normalized to forward slashes."""
        prompt = OfflineLLMConnector._build_prompt(
            file_path="c:\\workspace\\app\\main.py",
            code_snippet="import sys",
            architectural_issue="God Object"
        )
        self.assertNotIn("c:\\workspace\\app\\main.py", prompt)
        self.assertIn("c:/workspace/app/main.py", prompt)

    def test_default_endpoints_structure(self):
        """Asserts default endpoint map contains standard local AI ports."""
        endpoints = OfflineLLMConnector.DEFAULT_ENDPOINTS
        self.assertIn("ollama", endpoints)
        self.assertIn("lm_studio", endpoints)
        self.assertIn("openai_proxy", endpoints)


if __name__ == "__main__":
    unittest.main()
