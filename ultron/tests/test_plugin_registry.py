"""
Ultron Unit Tests for Modular Analytical Plugin Registry
"""
import unittest
from ultron.core.plugin_registry import AnalysisPluginRegistry

class TestPluginRegistry(unittest.TestCase):
    def setUp(self):
        AnalysisPluginRegistry.clear()

    def test_register_and_run_plugins(self):
        def sample_security_pass(ctx):
            return {"vulnerabilities_found": 0, "status": "clean"}

        AnalysisPluginRegistry.register_plugin("security_pass", sample_security_pass)
        res = AnalysisPluginRegistry.run_all_plugins({"file.py": {}})

        self.assertIn("security_pass", res)
        self.assertEqual(res["security_pass"]["status"], "clean")

    def test_plugin_exception_isolation(self):
        def failing_pass(ctx):
            raise RuntimeError("Corrupted plugin AST parse")

        AnalysisPluginRegistry.register_plugin("failing_pass", failing_pass)
        res = AnalysisPluginRegistry.run_all_plugins({})

        self.assertIn("failing_pass", res)
        self.assertEqual(res["failing_pass"]["status"], "failed")

if __name__ == "__main__":
    unittest.main()
