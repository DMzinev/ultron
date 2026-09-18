"""
ultron.tests.test_sarif_export
Hermetic test suite for native OASIS SARIF 2.1.0 Static Analysis Export.
Verifies compliance with GitHub Code Scanning, schema constraints, dynamic rule registration,
Windows-safe atomic writes, and CLI/Action integrations.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from ultron.core.sarif_reporter import (
    SARIFReporter,
    SARIF_SCHEMA_URI,
    SARIF_VERSION,
    normalize_sarif_uri,
    map_severity_to_sarif_level
)
from ultron.interfaces.cli.commands.gate import run_gate_command


class TestSARIFExport(unittest.TestCase):
    """Hermetic unit tests for SARIF 2.1.0 static analysis reporting."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sarif_schema_and_version_compliance(self):
        """Validates that SARIF output adheres to OASIS SARIF 2.1.0 top-level envelope."""
        sarif = SARIFReporter.generate_sarif_report({}, repo_path=self.repo_dir)
        self.assertEqual(sarif["$schema"], SARIF_SCHEMA_URI)
        self.assertEqual(sarif["version"], SARIF_VERSION)
        self.assertIn("runs", sarif)
        self.assertIsInstance(sarif["runs"], list)
        self.assertEqual(len(sarif["runs"]), 1)

    def test_sarif_tool_driver_metadata(self):
        """Validates driver name, version, and information URI metadata."""
        from ultron import get_version
        sarif = SARIFReporter.generate_sarif_report({}, repo_path=self.repo_dir, driver_version="1.5.0")
        driver = sarif["runs"][0]["tool"]["driver"]
        self.assertEqual(driver["name"], "Ultron")
        self.assertEqual(driver["version"], "1.5.0")
        self.assertEqual(driver["semanticVersion"], "1.5.0")
        self.assertEqual(driver["version"], get_version())
        self.assertIn("github.com/DMzinev/ultron", driver["informationUri"])

        # Also verify default parameter dynamically resolves get_version() and 1.5.0
        sarif_default = SARIFReporter.generate_sarif_report({}, repo_path=self.repo_dir)
        driver_default = sarif_default["runs"][0]["tool"]["driver"]
        self.assertEqual(driver_default["version"], get_version())
        self.assertEqual(driver_default["version"], "1.5.0")

    def test_sarif_canonical_rules_inventory(self):
        """Validates that all default canonical rules are present in tool driver descriptors."""
        sarif = SARIFReporter.generate_sarif_report({}, repo_path=self.repo_dir)
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = {r["id"] for r in rules}

        expected_rules = {
            "ULTRON-CIRCULAR-DEP",
            "ULTRON-RISK-CRITICAL",
            "ULTRON-RISK-HIGH",
            "ULTRON-COMPLEXITY-HOTSPOT",
            "ULTRON-COUPLING-BOTTLENECK"
        }
        for exp in expected_rules:
            self.assertIn(exp, rule_ids)

    def test_sarif_policy_violations_mapping_and_dynamic_rules(self):
        """
        Validates that policy violations are mapped into results and custom policy rules
        are dynamically registered in tool.driver.rules (Directives 1 & 2).
        """
        analysis = {
            "policy_violations": [
                {
                    "rule_id": "CUSTOM-NO-GOD-OBJECT",
                    "rule_name": "No God Objects",
                    "severity": "CRITICAL",
                    "source_file": "core\\engine.py",
                    "line": 42,
                    "message": "Class GodObject exceeds 50 methods.",
                    "remediation": "Decompose into smaller services."
                }
            ]
        }

        sarif = SARIFReporter.generate_sarif_report(analysis, repo_path=self.repo_dir)
        run = sarif["runs"][0]
        results = run["results"]
        rules = run["tool"]["driver"]["rules"]

        # Dynamic rule registration
        registered_ids = {r["id"]: r for r in rules}
        self.assertIn("CUSTOM-NO-GOD-OBJECT", registered_ids)
        custom_rule = registered_ids["CUSTOM-NO-GOD-OBJECT"]
        self.assertEqual(custom_rule["defaultConfiguration"]["level"], "error")

        # Result mapping
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["ruleId"], "CUSTOM-NO-GOD-OBJECT")
        self.assertEqual(res["level"], "error")
        self.assertIn("Decompose into smaller services", res["message"]["text"])
        self.assertEqual(res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "core/engine.py")
        self.assertEqual(res["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"], "%SRCROOT%")
        self.assertEqual(res["locations"][0]["physicalLocation"]["region"]["startLine"], 42)

    def test_sarif_circular_dependency_mapping(self):
        """Validates that cyclic dependencies are mapped to ULTRON-CIRCULAR-DEP results."""
        analysis = {
            "circular_dependencies": [
                {
                    "nodes": ["ultron/core/a.py", "ultron/core/b.py", "ultron/core/a.py"],
                    "cycle": ["ultron/core/a.py", "ultron/core/b.py", "ultron/core/a.py"],
                    "severity": "HIGH",
                    "length": 2
                }
            ]
        }

        sarif = SARIFReporter.generate_sarif_report(analysis, repo_path=self.repo_dir)
        results = sarif["runs"][0]["results"]
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["ruleId"], "ULTRON-CIRCULAR-DEP")
        self.assertEqual(res["level"], "error")
        self.assertEqual(res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "ultron/core/a.py")
        self.assertIn("ultron/core/b.py", res["message"]["text"])

    def test_sarif_risk_hotspots_mapping(self):
        """Validates that HIGH and CRITICAL risk items produce distinct SARIF results."""
        analysis = {
            "risks": [
                {
                    "file_path": "legacy/spaghetti.py",
                    "level": "CRITICAL",
                    "complexity": 35,
                    "coupling_score": 0.85,
                    "mitigation": "Split module into smaller components."
                },
                {
                    "file_path": "legacy/busy.py",
                    "level": "HIGH",
                    "complexity": 22,
                    "coupling_score": 0.55,
                    "mitigation": "Refactor complex methods."
                },
                {
                    "file_path": "clean/simple.py",
                    "level": "LOW",
                    "complexity": 3,
                    "coupling_score": 0.1
                }
            ]
        }

        sarif = SARIFReporter.generate_sarif_report(analysis, repo_path=self.repo_dir)
        results = sarif["runs"][0]["results"]
        # Only CRITICAL and HIGH should produce risk results
        self.assertEqual(len(results), 2)
        rule_ids = {r["ruleId"] for r in results}
        self.assertIn("ULTRON-RISK-CRITICAL", rule_ids)
        self.assertIn("ULTRON-RISK-HIGH", rule_ids)

    def test_sarif_clean_repository_empty_results(self):
        """Validates that a clean repository produces zero SARIF results but valid envelope."""
        sarif = SARIFReporter.generate_sarif_report({"risks": [], "policy_violations": []}, repo_path=self.repo_dir)
        self.assertEqual(sarif["runs"][0]["results"], [])

    def test_sarif_write_file_atomic_and_dir_creation(self):
        """Validates atomic writing with parent directory creation and handle closure."""
        out_path = os.path.join(self.repo_dir, "nested", "reports", "scan_results.sarif")
        payload = SARIFReporter.generate_sarif_report({}, repo_path=self.repo_dir)

        written_path = SARIFReporter.write_sarif_file(payload, out_path)
        self.assertTrue(os.path.exists(written_path))

        with open(written_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["version"], "2.1.0")

    def test_normalize_sarif_uri_resilience(self):
        """Tests URI normalization across Windows backslashes, leading prefixes, and absolute paths."""
        self.assertEqual(normalize_sarif_uri("src\\main.py"), "src/main.py")
        self.assertEqual(normalize_sarif_uri("./src/main.py"), "src/main.py")
        self.assertEqual(normalize_sarif_uri("/src/main.py"), "src/main.py")
        self.assertEqual(normalize_sarif_uri(""), "unknown")
        self.assertEqual(normalize_sarif_uri(None), "unknown")

        abs_file = os.path.join(self.repo_dir, "sub", "app.py")
        norm = normalize_sarif_uri(abs_file, repo_path=self.repo_dir)
        self.assertEqual(norm, "sub/app.py")

    def test_map_severity_to_sarif_level(self):
        """Validates severity mapping to standard SARIF 2.1.0 levels."""
        self.assertEqual(map_severity_to_sarif_level("CRITICAL"), "error")
        self.assertEqual(map_severity_to_sarif_level("HIGH"), "error")
        self.assertEqual(map_severity_to_sarif_level("MEDIUM"), "warning")
        self.assertEqual(map_severity_to_sarif_level("LOW"), "note")
        self.assertEqual(map_severity_to_sarif_level("UNKNOWN"), "note")

    def test_gate_cli_sarif_flag_export(self):
        """Validates that run_gate_command writes a SARIF file when sarif_output is specified."""
        sarif_target = os.path.join(self.repo_dir, "artifacts", "gate_results.sarif")
        
        mock_analysis = {
            "repo": self.repo_dir,
            "risks": [
                {
                    "file_path": "bad_code.py",
                    "level": "HIGH",
                    "complexity": 25,
                    "coupling_score": 0.7
                }
            ],
            "policy_violations": [],
            "health_score": 75.0,
            "total_files": 1
        }

        with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
            exit_code = run_gate_command(
                repo_path=self.repo_dir,
                sarif_output=sarif_target,
                fail_on_regression=False,
                json_output=True
            )

        self.assertTrue(os.path.exists(sarif_target))
        with open(sarif_target, "r", encoding="utf-8") as f:
            sarif_doc = json.load(f)
        self.assertEqual(sarif_doc["version"], "2.1.0")
        self.assertEqual(len(sarif_doc["runs"][0]["results"]), 1)

    def test_action_yml_sarif_input_declared(self):
        """Validates that .github/actions/ultron-gate/action.yml defines sarif-output input."""
        action_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", ".github", "actions", "ultron-gate", "action.yml")
        )
        self.assertTrue(os.path.exists(action_path), f"action.yml missing at {action_path}")
        with open(action_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("sarif-output:", content)
        self.assertIn("--sarif", content)


if __name__ == "__main__":
    unittest.main()
