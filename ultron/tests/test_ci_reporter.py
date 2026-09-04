"""
ultron.tests.test_ci_reporter
Unit test suite asserting CI/CD GitHub Action PR comment generation and quality regression gates.
"""

import unittest
import tempfile
import os
import shutil
from ultron.core.ci_reporter import CIReporter
from ultron.interfaces.cli.commands.ci import run_ci_command


class TestCIReporter(unittest.TestCase):
    """Unit tests for CIReporter and CI CLI command."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_pr_comment_structure(self):
        """Asserts generated PR comment contains shields, KPIs, and table headers."""
        current = {
            "health_score": 92.5,
            "risks": [
                {"file_path": "core/engine.py", "complexity": 14, "coupling_score": 6, "impact_score": 8.5, "level": "HIGH"}
            ],
            "policy_violations": []
        }
        baseline = {
            "health_score": 95.0,
            "risks": [
                {"file_path": "core/engine.py", "complexity": 12, "coupling_score": 5, "impact_score": 7.0, "level": "MEDIUM"}
            ],
            "policy_violations": []
        }

        comment = CIReporter.generate_pr_comment(current, baseline, project_name="Ultron Engine")
        self.assertIn("## 🏛️ Ultron Engine — CI/CD Architectural Gate", comment)
        self.assertIn("https://img.shields.io/badge/Architecture_Gate-PASSED-brightgreen", comment)
        self.assertIn("| **Health Score** |", comment)
        self.assertIn("core/engine.py", comment)
        self.assertIn("Top 5 High-Impact File Hotspots", comment)

    def test_evaluate_regression_gate_clean_pass(self):
        """Asserts regression gate passes when health score is stable or improves."""
        current = {"health_score": 96.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], 1.0)
        self.assertEqual(len(gate["reasons"]), 0)

    def test_evaluate_regression_gate_health_drop(self):
        """Asserts regression gate trips when health drop exceeds max_health_drop."""
        current = {"health_score": 80.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 90.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=5.0)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["health_delta"], -10.0)
        self.assertIn("dropped by 10.0 pts", gate["reasons"][0])

    def test_evaluate_regression_gate_high_policy_violation(self):
        """Asserts regression gate trips on HIGH or CRITICAL policy violations."""
        current = {
            "health_score": 95.0,
            "risks": [],
            "policy_violations": [
                {"severity": "HIGH", "rule_type": "LAYER_ISOLATION", "source": "db.py", "message": "Direct UI import"}
            ]
        }
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, fail_on_high=True)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["high_violations_count"], 1)
        self.assertIn("HIGH/CRITICAL policy violation(s)", gate["reasons"][0])

    def test_missing_baseline_fallback(self):
        """Asserts graceful handling when baseline analysis is None."""
        current = {"health_score": 88.0, "risks": [], "policy_violations": []}
        gate = CIReporter.evaluate_regression_gate(current, None)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], 0.0)

        comment = CIReporter.generate_pr_comment(current, None)
        self.assertIn("88.0 / 100", comment)

    def test_run_ci_command_file_output(self):
        """Asserts CLI run_ci_command outputs file correctly."""
        out_file = os.path.join(self.temp_dir, "pr_comment.md")
        code = run_ci_command(
            repo_path=self.temp_dir,
            output_comment_path=out_file,
            fail_on_regression=False
        )
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out_file))
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("CI/CD Architectural Gate", content)


if __name__ == "__main__":
    unittest.main()
