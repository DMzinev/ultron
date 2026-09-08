"""
ultron/tests/test_ci_gate_contract.py
Validates Task D2: Machine-Readable Contract + CI Gate.
Verifies versioned brief schema (schema_version: 1.0.0), --max-high and --min-health
gate thresholds, exit codes (0 = PASS, 1 = FAIL), and GitHub Actions annotations.
"""

import os
import io
import sys
import json
import unittest
from unittest.mock import patch

from ultron.interfaces.cli.commands.brief import run_brief_command
from ultron.interfaces.cli.commands.gate import run_gate_command
from ultron.core.ci_reporter import CIReporter, _escape_gha_data, _escape_gha_prop
from ultron.interfaces.server import UltronAPIHandler

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))


class TestCIGateContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean_repo = os.path.join(FIXTURES_DIR, "clean_repo")
        cls.tangled_repo = os.path.join(FIXTURES_DIR, "tangled_repo")
        cls.mixed_repo = os.path.join(FIXTURES_DIR, "mixed_repo")

    def test_brief_command_json_schema(self):
        """Verify 'ultron brief <file> --json' produces versioned contract with 7 envelope fields and AST facts."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_brief_command("service.py", repo_path=self.clean_repo, json_output=True)

        self.assertEqual(code, 0, "run_brief_command should exit 0 on existing file")
        output = buf.getvalue().strip()
        data = json.loads(output)

        # 1. Schema version and top-level keys
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertEqual(data["target_file"], "service.py")
        self.assertIn("envelope", data)
        self.assertIn("analysis", data)
        self.assertIn("generated_at", data)

        # 2. 7-field mission envelope verification
        envelope = data["envelope"]
        for field in [
            "intent", "target_file", "blast_radius", "must_not_touch",
            "complexity_ceiling", "verification_command", "rollback_instruction",
            "token_budget_hint", "rendered_prompt"
        ]:
            self.assertIn(field, envelope)
            self.assertTrue(envelope[field], f"Field {field} should not be empty")

        self.assertEqual(envelope["blast_radius"], ["handlers.py"])
        self.assertEqual(envelope["rollback_instruction"], "git restore service.py")

        # 3. AST facts
        analysis = data["analysis"]
        self.assertEqual(analysis["complexity"], 2)
        self.assertEqual(analysis["callers"], ["handlers.py"])
        self.assertIsInstance(analysis["definitions"], list)
        self.assertIsInstance(analysis["imports"], list)

    def test_brief_command_markdown_output(self):
        """Verify 'ultron brief <file>' renders complete markdown prompt without --json."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_brief_command("service.py", repo_path=self.clean_repo, json_output=False)

        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("=== ULTRON PRE-EXECUTION INTELLIGENCE LAYER: MISSION ENVELOPE ===", output)
        for sec in [
            "[1. INTENT]", "[2. BLAST RADIUS]", "[3. MUST-NOT-TOUCH LIST]",
            "[4. COMPLEXITY CEILING]", "[5. VERIFICATION COMMAND]",
            "[6. ROLLBACK INSTRUCTION]", "[7. TOKEN BUDGET HINT]"
        ]:
            self.assertIn(sec, output)

    def test_brief_command_missing_file(self):
        """Verify 'ultron brief' exits 1 with clear diagnostic on missing file."""
        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            code = run_brief_command("nonexistent_file_xyz.py", repo_path=self.clean_repo)

        self.assertEqual(code, 1)
        self.assertIn("does not exist", err_buf.getvalue())

    def test_gate_max_high_enforcement(self):
        """Verify --max-high fails when HIGH risk count exceeds limit, and passes when within limit."""
        # mixed_repo has exactly 2 planted HIGH risk files (risky_core.py, risky_dispatcher.py)
        # --max-high 1 should FAIL (exit 1)
        exit_code_fail = run_gate_command(
            repo_path=self.mixed_repo,
            max_high=1,
            json_output=True
        )
        self.assertEqual(exit_code_fail, 1, "--max-high 1 must fail on mixed_repo (found 2 HIGH)")

        # --max-high 2 should PASS (exit 0)
        exit_code_pass = run_gate_command(
            repo_path=self.mixed_repo,
            max_high=2,
            json_output=True
        )
        self.assertEqual(exit_code_pass, 0, "--max-high 2 must pass on mixed_repo (found 2 HIGH <= 2)")

    def test_gate_min_health_enforcement(self):
        """Verify --min-health fails when health score drops below threshold, and passes when above."""
        # tangled_repo has calibrated health score ~22.3
        # --min-health 50 should FAIL (exit 1)
        exit_code_fail = run_gate_command(
            repo_path=self.tangled_repo,
            min_health=50.0,
            json_output=True
        )
        self.assertEqual(exit_code_fail, 1, "--min-health 50.0 must fail on tangled_repo (health ~22.3)")

        # --min-health 20 should PASS (exit 0)
        exit_code_pass = run_gate_command(
            repo_path=self.tangled_repo,
            min_health=20.0,
            json_output=True
        )
        self.assertEqual(exit_code_pass, 0, "--min-health 20.0 must pass on tangled_repo (health ~22.3 >= 20.0)")

    def test_gate_clean_repo_passes_all(self):
        """Verify clean_repo passes strict zero-high and high-health gates."""
        exit_code = run_gate_command(
            repo_path=self.clean_repo,
            max_high=0,
            min_health=80.0,
            json_output=True
        )
        self.assertEqual(exit_code, 0, "clean_repo must pass max_high=0 and min_health=80.0")

    def test_github_actions_annotation_escaping(self):
        """Verify GitHub Actions character escaping rules (%0A, %25, %3A, %2C)."""
        self.assertEqual(_escape_gha_data("line1\nline2"), "line1%0Aline2")
        self.assertEqual(_escape_gha_data("100% test"), "100%25 test")
        self.assertEqual(_escape_gha_prop("key:val,extra"), "key%3Aval%2Cextra")

    def test_github_actions_annotations_emitted(self):
        """Verify GitHub Actions annotations are generated and formatted with ::error / ::notice."""
        mock_analysis = {
            "repo": self.mixed_repo,
            "policy_violations": [
                {
                    "file": os.path.join(self.mixed_repo, "risky_core.py"),
                    "line": 12,
                    "severity": "CRITICAL",
                    "rule_id": "NO_GOD_MODULE",
                    "details": "Class exceeds complexity threshold."
                }
            ],
            "risks": [
                {
                    "file_path": os.path.join(self.mixed_repo, "risky_core.py"),
                    "level": "HIGH",
                    "complexity": 22,
                    "impact_score": 14.5
                }
            ]
        }
        gate_decision = {
            "passed": False,
            "reasons": ["Found 1 HIGH risk file", "Found 1 CRITICAL policy violation"],
            "current_health": 43.3
        }

        annotations = CIReporter.format_github_annotations(gate_decision, mock_analysis)
        self.assertTrue(len(annotations) >= 3)

        # Assert policy violation annotation
        policy_ann = [a for a in annotations if "NO_GOD_MODULE" in a][0]
        self.assertTrue(policy_ann.startswith("::error file=risky_core.py,line=12,"))

        # Assert risk hotspot annotation
        risk_ann = [a for a in annotations if "High Architectural Risk" in a][0]
        self.assertTrue(risk_ann.startswith("::error file=risky_core.py,line=1,"))

        # Assert overall gate failure annotation
        gate_ann = [a for a in annotations if "Quality Gate FAILED" in a][0]
        self.assertTrue(gate_ann.startswith("::error title="))

    def test_github_actions_annotations_policy_engine_source_file(self):
        """Verify policy violations with source_file (e.g. from PolicyEngine) resolve file correctly."""
        mock_analysis = {
            "repo": self.mixed_repo,
            "policy_violations": [
                {
                    "source_file": os.path.join(self.mixed_repo, "risky_core.py"),
                    "target_file": None,
                    "line": 15,
                    "severity": "HIGH",
                    "rule_id": "MAX_COMPLEXITY",
                    "details": "Cyclomatic complexity exceeds threshold."
                }
            ],
            "risks": []
        }
        gate_decision = {
            "passed": False,
            "reasons": ["Policy violation"],
            "current_health": 50.0
        }

        annotations = CIReporter.format_github_annotations(gate_decision, mock_analysis)
        policy_ann = [a for a in annotations if "MAX_COMPLEXITY" in a][0]
        self.assertTrue(policy_ann.startswith("::error file=risky_core.py,line=15,title="))

    def test_github_actions_annotations_empty_file_no_leading_comma(self):
        """Verify that when a violation or risk has no file path, command has space and NO leading comma."""
        mock_analysis = {
            "repo": "",
            "policy_violations": [
                {
                    "file": "",
                    "source_file": "",
                    "line": 1,
                    "severity": "LOW",
                    "rule_id": "GENERAL_VIOLATION",
                    "details": "General issue."
                }
            ],
            "risks": [
                {
                    "file": "",
                    "level": "HIGH",
                    "complexity": 10,
                    "impact_score": 12.0
                }
            ]
        }
        gate_decision = {"passed": True, "current_health": 100.0}

        annotations = CIReporter.format_github_annotations(gate_decision, mock_analysis)
        for ann in annotations:
            # Command must be separated from properties by space, never "::command,"
            self.assertFalse("::warning," in ann)
            self.assertFalse("::error," in ann)
            self.assertFalse("::notice," in ann)

        vio_ann = [a for a in annotations if "GENERAL_VIOLATION" in a][0]
        self.assertTrue(vio_ann.startswith("::warning line=1,title="))

    def test_agent_routes_export_brief_schema_version(self):
        """Verify handle_v1_export_brief on AgentRoutesMixin returns schema_version: 1.0.0."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/export-brief"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.get_repo_root_path = lambda: self.clean_repo

        req_payload = {
            "repo": self.clean_repo,
            "format": "json"
        }
        handler.get_post_data = lambda: req_payload
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.send_json_response = lambda code, body: handler.wfile.write(json.dumps(body).encode("utf-8"))

        handler.handle_v1_export_brief()

        raw_output = handler.wfile.getvalue().decode("utf-8")
        res = json.loads(raw_output)

        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res.get("schema_version"), "1.0.0")
        self.assertIn("brief", res)
        self.assertEqual(res["brief"].get("schema_version"), "1.0.0")


if __name__ == "__main__":
    unittest.main()
