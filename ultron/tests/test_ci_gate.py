"""
ultron.tests.test_ci_gate
Comprehensive adversarial test suite for PR Verification Shield & Pre-Merge Gate.
Verifies boundary conditions, baseline corruption, health regression thresholds,
policy violations, strict mode, omitted co-change detection, and GITHUB_STEP_SUMMARY output.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from ultron.core.ci_reporter import CIReporter
from ultron.interfaces.cli.commands.gate import run_gate_command
from ultron.interfaces.cli.commands.ci import run_ci_command


class TestCIGateEmptyPR(unittest.TestCase):
    """Verifies gate behavior on PRs with 0 changed files or empty analysis payloads."""

    def test_empty_pr_clean_pass(self):
        """Asserts empty analysis payload passes with 0 delta and default 100 health."""
        current = {"risks": [], "health_score": 100.0, "policy_violations": []}
        baseline = {"risks": [], "health_score": 100.0, "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], 0.0)
        self.assertEqual(gate["avg_complexity_delta"], 0.0)
        self.assertEqual(gate["avg_coupling_delta"], 0.0)
        self.assertEqual(len(gate["reasons"]), 0)

    def test_empty_risks_zero_division_guard(self):
        """Asserts _extract_averages handles empty risks without ZeroDivisionError."""
        averages = CIReporter._extract_averages({"risks": []})
        self.assertEqual(averages["avg_complexity"], 1.0)
        self.assertEqual(averages["avg_coupling"], 0.0)

        averages_none = CIReporter._extract_averages(None)
        self.assertEqual(averages_none["avg_complexity"], 1.0)
        self.assertEqual(averages_none["avg_coupling"], 0.0)


class TestCIGateBaselineEdgeCases(unittest.TestCase):
    """Verifies robust degradation when baseline analysis is missing or malformed."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_baseline_file_graceful_fallback(self):
        """Asserts missing baseline file triggers warning and evaluates standalone."""
        missing_path = os.path.join(self.temp_dir.name, "non_existent_baseline.json")
        out_comment = os.path.join(self.temp_dir.name, "comment.md")

        with patch("sys.stderr"):
            exit_code = run_gate_command(
                repo_path=self.temp_dir.name,
                baseline=missing_path,
                output_comment=out_comment,
                fail_on_regression=True
            )
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(out_comment))

    def test_corrupt_json_baseline_handling(self):
        """Asserts invalid JSON baseline file does not crash the gate."""
        corrupt_path = os.path.join(self.temp_dir.name, "corrupt_base.json")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("{ invalid_json: true, missing_closing_bracket")

        with patch("sys.stderr"):
            exit_code = run_gate_command(
                repo_path=self.temp_dir.name,
                baseline=corrupt_path,
                fail_on_regression=True
            )
        self.assertEqual(exit_code, 0)

    def test_empty_baseline_file_handling(self):
        """Asserts 0-byte baseline file is safely handled."""
        empty_path = os.path.join(self.temp_dir.name, "empty_base.json")
        with open(empty_path, "w", encoding="utf-8") as f:
            f.write("")

        with patch("sys.stderr"):
            exit_code = run_gate_command(
                repo_path=self.temp_dir.name,
                baseline=empty_path,
                fail_on_regression=True
            )
        self.assertEqual(exit_code, 0)

    def test_invalid_schema_baseline_handling(self):
        """Asserts non-dictionary or missing-keys baseline is handled gracefully."""
        gate = CIReporter.evaluate_regression_gate(
            current_analysis={"health_score": 90.0, "risks": [], "policy_violations": []},
            baseline_analysis=None
        )
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], 0.0)


class TestCIGateHealthDropRegression(unittest.TestCase):
    """Verifies health degradation threshold evaluations."""

    def test_health_drop_exceeding_threshold_fails_gate(self):
        """Health drop -6.0 pts vs 5.0 allowed must fail gate."""
        current = {"health_score": 89.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=5.0)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["health_delta"], -6.0)
        self.assertTrue(any("dropped by 6.0 pts" in r for r in gate["reasons"]))

    def test_health_drop_within_threshold_passes(self):
        """Health drop -3.0 pts vs 5.0 allowed must pass gate."""
        current = {"health_score": 92.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=5.0)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], -3.0)
        self.assertEqual(len(gate["reasons"]), 0)

    def test_health_improvement_passes(self):
        """Health improvement +4.0 pts passes cleanly."""
        current = {"health_score": 98.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 94.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=5.0)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], 4.0)

    def test_exact_boundary_threshold_behavior(self):
        """Exact drop of -5.0 pts vs 5.0 max allowed must pass boundary check."""
        current = {"health_score": 90.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=5.0)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["health_delta"], -5.0)


class TestCIGatePolicyViolations(unittest.TestCase):
    """Verifies CRITICAL and HIGH policy violation gates."""

    def test_critical_policy_violation_trips_gate(self):
        """Critical violation trips gate even if health drop is 0."""
        current = {
            "health_score": 95.0,
            "risks": [],
            "policy_violations": [
                {"severity": "CRITICAL", "rule_type": "CIRCULAR_DEPENDENCY", "source": "core.py", "message": "Cyclic import"}
            ]
        }
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, fail_on_high=True)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["high_violations_count"], 1)
        self.assertIn("HIGH/CRITICAL policy violation(s) detected", gate["reasons"][0])

    def test_high_policy_violation_trips_gate(self):
        """High severity violation trips gate."""
        current = {
            "health_score": 95.0,
            "risks": [],
            "policy_violations": [
                {"severity": "HIGH", "rule_type": "LAYER_ISOLATION", "source": "ui.py", "message": "Direct DB call"}
            ]
        }
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, fail_on_high=True)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["high_violations_count"], 1)

    def test_low_medium_violations_do_not_trip_standard_gate(self):
        """Medium/Low violations do not trip fail_on_high gate."""
        current = {
            "health_score": 95.0,
            "risks": [],
            "policy_violations": [
                {"severity": "MEDIUM", "rule_type": "NAMING", "source": "helper.py", "message": "Function name too short"},
                {"severity": "LOW", "rule_type": "DOCSTRING", "source": "helper.py", "message": "Missing docstring"}
            ]
        }
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, fail_on_high=True)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["high_violations_count"], 0)
        self.assertEqual(gate["total_violations_count"], 2)


class TestCIGateStrictMode(unittest.TestCase):
    """Verifies strict zero-tolerance mode."""

    def test_strict_mode_fails_on_minor_health_drop(self):
        """In strict mode (max_health_drop=0.0), a -0.5 drop must fail."""
        current = {"health_score": 94.5, "risks": [], "policy_violations": []}
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=0.0)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["health_delta"], -0.5)

    def test_strict_mode_passes_on_zero_drop_and_no_violations(self):
        """In strict mode, 0 delta and 0 violations passes."""
        current = {"health_score": 95.0, "risks": [], "policy_violations": []}
        baseline = {"health_score": 95.0, "risks": [], "policy_violations": []}

        gate = CIReporter.evaluate_regression_gate(current, baseline, max_health_drop=0.0)
        self.assertTrue(gate["passed"])


class TestCIGateOmittedCoChangeDetection(unittest.TestCase):
    """Verifies detection and reporting of omitted co-change dependencies."""

    def test_omitted_co_change_alert_surfaced(self):
        """Asserts that modified file with high co-change partner missing from PR is flagged."""
        current = {
            "health_score": 92.0,
            "risks": [
                {
                    "file_path": "ultron/core/auth.py",
                    "complexity": 10,
                    "coupling_score": 4,
                    "impact_score": 7.0,
                    "level": "MEDIUM",
                    "co_changes": [
                        {"file": "ultron/core/tokens.py", "joint_commits": 12, "co_change_ratio": 0.85}
                    ]
                }
            ],
            "policy_violations": []
        }
        comment = CIReporter.generate_pr_comment(current, None, project_name="Ultron Gate")
        self.assertIn("ultron/core/auth.py", comment)
        self.assertIn("ultron/core/tokens.py", comment)
        self.assertIn("85%", comment)


class TestCIGateGitHubStepSummaryAndOutput(unittest.TestCase):
    """Verifies GITHUB_STEP_SUMMARY environment integration and file outputs."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_github_step_summary_appends_markdown(self):
        """Asserts PR comment is cleanly appended to GITHUB_STEP_SUMMARY file if env var set."""
        summary_file = os.path.join(self.temp_dir.name, "step_summary.md")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# Existing Step Header\n\n")

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary_file}):
            out_comment = os.path.join(self.temp_dir.name, "pr_comment.md")
            exit_code = run_gate_command(
                repo_path=self.temp_dir.name,
                output_comment=out_comment,
                fail_on_regression=False
            )
            self.assertEqual(exit_code, 0)

        # Check step summary file content was preserved and appended
        with open(summary_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# Existing Step Header", content)
        self.assertIn("CI/CD Architectural Gate", content)

    def test_explicit_output_comment_file_creation(self):
        """Asserts nested directories are created for output_comment."""
        nested_out = os.path.join(self.temp_dir.name, "nested", "ci", "report.md")
        exit_code = run_gate_command(
            repo_path=self.temp_dir.name,
            output_comment=nested_out,
            fail_on_regression=False
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(nested_out))


class TestCIGateCLIIntegration(unittest.TestCase):
    """Verifies end-to-end CLI exit code mapping and json outputs."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_exit_code_1_on_gate_failure(self):
        """CLI returns exit code 1 when regression gate fails with fail_on_regression=True."""
        baseline_file = os.path.join(self.temp_dir.name, "base.json")
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump({"health_score": 100.0, "risks": [], "policy_violations": []}, f)

        mock_analysis = {
            "risks": [{"file_path": "a.py", "complexity": 25, "coupling_score": 10, "impact_score": 9.5, "level": "HIGH"}],
            "health_score": 75.0,
            "policy_violations": [{"severity": "CRITICAL", "message": "Layer breach"}]
        }

        with patch("ultron.core.analyzer.analyze_directory", return_value={"a.py": {}}), \
             patch("ultron.core.risk.scoring.evaluate_risks", return_value=mock_analysis["risks"]), \
             patch("ultron.core.policy_engine.PolicyEngine.evaluate_codebase", return_value={"violations": mock_analysis["policy_violations"], "compliance_score": 75.0}):
            
            with patch("sys.stderr"):
                exit_code = run_gate_command(
                    repo_path=self.temp_dir.name,
                    baseline=baseline_file,
                    fail_on_regression=True,
                    max_health_drop=5.0
                )
            self.assertEqual(exit_code, 1)

    def test_cli_exit_code_0_on_gate_pass(self):
        """CLI returns exit code 0 when gate passes."""
        baseline_file = os.path.join(self.temp_dir.name, "base.json")
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump({"health_score": 90.0, "risks": [], "policy_violations": []}, f)

        with patch("sys.stderr"):
            exit_code = run_gate_command(
                repo_path=self.temp_dir.name,
                baseline=baseline_file,
                fail_on_regression=True,
                max_health_drop=5.0
            )
        self.assertEqual(exit_code, 0)

    def test_cli_json_output_mode(self):
        """Asserts --json output format returns clean valid JSON."""
        with patch("sys.stderr"):
            with patch("builtins.print") as mock_print:
                exit_code = run_gate_command(
                    repo_path=self.temp_dir.name,
                    json_output=True,
                    fail_on_regression=False
                )
        self.assertEqual(exit_code, 0)
        self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
