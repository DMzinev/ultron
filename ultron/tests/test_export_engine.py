"""
ultron.tests.test_export_engine
Unit test suite asserting deterministic standalone HTML, Markdown, and JSON exports.
"""

import json
import unittest
from ultron.core.export_engine import ExportEngine, norm_path


class TestExportEngine(unittest.TestCase):
    """Unit tests for ExportEngine."""

    def setUp(self):
        self.sample_data = {
            "project_name": "SampleApp",
            "risks": [
                {"file": "controller.py", "complexity": 6.0, "coupling_score": 3.0, "impact_score": 12.5},
                {"file": "service.py", "complexity": 3.0, "coupling_score": 1.0, "impact_score": 4.2}
            ],
            "modularity": {
                "health_score": 88.5,
                "grade": "A",
                "mean_instability": 0.35,
                "mean_distance": 0.12
            },
            "anti_patterns": [
                {
                    "severity": "HIGH",
                    "pattern_name": "God Object",
                    "file_path": "controller.py",
                    "playbook": "Extract cohesive subroutines."
                }
            ],
            "recommendations": [
                {"title": "Decouple Controller", "description": "Split business logic into dedicated services."}
            ]
        }

    def test_norm_path(self):
        """Asserts path normalization to POSIX slashes."""
        self.assertEqual(norm_path("ultron\\core\\export_engine.py"), "ultron/core/export_engine.py")
        self.assertEqual(norm_path(None), "")

    def test_generate_json_bundle_validity(self):
        """Asserts JSON bundle serialization and structure."""
        bundle_str = ExportEngine.generate_json_bundle(self.sample_data)
        parsed = json.loads(bundle_str)
        self.assertEqual(parsed["export_type"], "ultron_architecture_bundle")
        self.assertEqual(parsed["data"]["project_name"], "SampleApp")

    def test_generate_markdown_dossier_structure(self):
        """Asserts Markdown dossier contains key headers, metrics, and tables."""
        md = ExportEngine.generate_markdown_dossier(self.sample_data, project_name="SampleApp")
        self.assertIn("# 🛡️ Ultron Executive Architecture Dossier: SampleApp", md)
        self.assertIn("Architectural Health Grade", md)
        self.assertIn("`A` (88.5 / 100)", md)
        self.assertIn("| `controller.py` | 12.50 | 6.0 | 3.0 | ⚠️ REVIEW |", md)
        self.assertIn("God Object", md)
        self.assertIn("Decouple Controller", md)

    def test_generate_standalone_html_structure(self):
        """Asserts standalone HTML contains doctype, styling, and data rows."""
        html_content = ExportEngine.generate_standalone_html(self.sample_data, project_name="SampleApp")
        self.assertTrue(html_content.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>Ultron Architecture Audit: SampleApp</title>", html_content)
        self.assertIn("<code>controller.py</code>", html_content)
        self.assertIn("12.50", html_content)
        self.assertIn("God Object", html_content)
        self.assertIn("</html>", html_content)

    def test_empty_input_resilience(self):
        """Asserts empty dictionary produces valid HTML and Markdown without exceptions."""
        empty_html = ExportEngine.generate_standalone_html({})
        self.assertTrue(empty_html.startswith("<!DOCTYPE html>"))
        self.assertIn("No module risk records found.", empty_html)

        empty_md = ExportEngine.generate_markdown_dossier({})
        self.assertIn("# 🛡️ Ultron Executive Architecture Dossier:", empty_md)

        empty_json = ExportEngine.generate_json_bundle(None)
        self.assertIn("ultron_architecture_bundle", empty_json)

    def test_html_escaping_xss_safety(self):
        """Asserts dangerous characters are escaped in HTML output."""
        malicious_data = {
            "project_name": "<script>alert('xss')</script>",
            "risks": [
                {"file": "<b>malicious.py</b>", "complexity": 1.0, "coupling_score": 0.0, "impact_score": 1.0}
            ]
        }
        safe_html = ExportEngine.generate_standalone_html(malicious_data)
        self.assertNotIn("<script>alert('xss')</script>", safe_html)
        self.assertIn("&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;", safe_html)
        self.assertIn("&lt;b&gt;malicious.py&lt;/b&gt;", safe_html)


if __name__ == "__main__":
    unittest.main()
