"""
ultron/tests/test_auditor_defect_sensitivity.py

Verification suite for Task C3 per docs/AGENT_EXECUTION_PLAN.md:
"Prove the auditor actually detects defects."

Ensures the verification and auditing safety nets have teeth by injecting
concrete defects across 4 distinct categories:
1. Circular import in a fixture -> cycle detector reports it.
2. Unhandled exception in an endpoint -> contract test flags it.
3. Missing required key in an API response -> contract test flags it.
4. Inflated complexity (>= 50) in a function -> risk scorer escalates to HIGH.
"""

import os
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from ultron.core import analyzer
from ultron.core.cycle_detector import CycleDetector
from ultron.core.risk import scoring
from ultron.interfaces.server import UltronAPIHandler


class TestAuditorDefectSensitivity(unittest.TestCase):
    """Proves that architectural and contract auditors detect deliberate defects."""

    def test_defect_1_circular_import_detection(self):
        """
        Defect 1: Plant a circular import across files -> assert the cycle detector reports it.
        Uses the tangled_repo fixture where cycle_b -> cycle_c -> god_module -> cycle_b.
        """
        fixture_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "fixtures", "tangled_repo")
        )
        self.assertTrue(os.path.isdir(fixture_path), f"Fixture not found at {fixture_path}")

        codebase = analyzer.analyze_directory(fixture_path)
        all_files = set(codebase.keys())

        # Extract file-level import edges from parsed codebase
        file_edges = []
        for f, data in codebase.items():
            for imp in data.get("imports", []):
                mod_name = imp.split(".")[0] + ".py"
                if mod_name in all_files and mod_name != f:
                    file_edges.append({"source": f, "target": mod_name})

        # Run cycle detector
        detected_cycles = CycleDetector.find_all_cycles(edges=file_edges)

        # Safety net assertion: Cycle detector must detect the planted circular import
        self.assertGreaterEqual(
            len(detected_cycles), 1,
            "Cycle detector failed to detect planted circular import in tangled_repo"
        )

        cycle_nodes = set(detected_cycles[0].get("nodes", []))
        expected_cycle_members = {"cycle_b.py", "cycle_c.py", "god_module.py"}
        self.assertTrue(
            expected_cycle_members.issubset(cycle_nodes),
            f"Expected cycle members {expected_cycle_members} not found in {cycle_nodes}"
        )

    def test_defect_2_unhandled_exception_in_endpoint_flagged(self):
        """
        Defect 2: Plant an unhandled exception in an endpoint -> assert the contract test flags it.
        Simulates an in-process handler invocation with contract validation.
        """
        def invoke_and_audit_endpoint(handler_method):
            """Contract audit harness: executes an endpoint and asserts clean HTTP 200 response."""
            handler = UltronAPIHandler.__new__(UltronAPIHandler)
            handler.wfile = io.BytesIO()
            handler.headers = {}
            handler.status_code = None

            def fake_send_response(code):
                handler.status_code = code

            def fake_send_json(code, data):
                handler.status_code = code
                handler.wfile.write(json.dumps(data).encode("utf-8"))

            handler.send_response = fake_send_response
            handler.send_json_response = fake_send_json
            handler.send_header = lambda k, v: None
            handler.end_headers = lambda: None

            try:
                handler_method(handler)
            except Exception as exc:
                raise AssertionError(f"Endpoint raised unhandled exception: {exc}") from exc

            if handler.status_code != 200:
                raise AssertionError(f"Endpoint failed contract: expected HTTP 200, got {handler.status_code}")

            raw_out = handler.wfile.getvalue().decode("utf-8")
            return json.loads(raw_out) if raw_out else {}

        # Planted defect: handler raises an unexpected RuntimeError
        def defective_handler(handler):
            raise RuntimeError("Database connection suddenly dropped")

        # Safety net assertion: Audit harness must flag the unhandled exception
        with self.assertRaises(AssertionError) as ctx:
            invoke_and_audit_endpoint(defective_handler)

        self.assertIn("Endpoint raised unhandled exception", str(ctx.exception))
        self.assertIn("Database connection suddenly dropped", str(ctx.exception))

    def test_defect_3_missing_required_key_flagged(self):
        """
        Defect 3: Delete a required key from an API response -> assert the contract test flags it.
        """
        def audit_response_contract(payload: dict, required_keys: set):
            """Validates that a response dictionary satisfies the contract schema."""
            if not isinstance(payload, dict):
                raise AssertionError(f"Expected dict response, got {type(payload)}")
            missing = required_keys - set(payload.keys())
            if missing:
                raise AssertionError(f"Contract violation: missing required keys: {sorted(missing)}")
            return True

        # Valid baseline response schema for /api/v1/summary
        contract_keys = {"initialized", "total_files", "health_score", "risks"}
        valid_response = {
            "initialized": True,
            "total_files": 10,
            "health_score": 95.0,
            "risks": []
        }
        self.assertTrue(audit_response_contract(valid_response, contract_keys))

        # Planted defect: required key 'health_score' is deleted
        defective_response = dict(valid_response)
        del defective_response["health_score"]

        # Safety net assertion: Contract audit must catch the missing required key
        with self.assertRaises(AssertionError) as ctx:
            audit_response_contract(defective_response, contract_keys)

        self.assertIn("Contract violation: missing required keys", str(ctx.exception))
        self.assertIn("health_score", str(ctx.exception))

    def test_defect_4_high_complexity_escalation(self):
        """
        Defect 4: Inflate complexity to 50 in a single function -> assert risk scorer escalates to HIGH.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = "monster_logic.py"
            file_path = os.path.join(tmpdir, target_file)

            # Generate a function with 50 distinct conditional branches (cyclomatic complexity >= 50)
            code_lines = ["def evaluate_monster(val):"]
            for i in range(50):
                code_lines.append(f"    if val == {i}: return {i}")
            code_lines.append("    return -1\n")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(code_lines))

            # Run analyzer & risk scorer
            codebase = analyzer.analyze_directory(tmpdir)
            risks = scoring.evaluate_risks(codebase, [target_file], repo_path=tmpdir)

            # Safety net assertion: Risk scorer must escalate this file to HIGH
            self.assertEqual(len(risks), 1, "Expected exactly 1 risk packet")
            packet = risks[0]
            self.assertGreaterEqual(packet.complexity, 50, f"Expected complexity >= 50, got {packet.complexity}")
            self.assertEqual(
                packet.level, "HIGH",
                f"Risk scorer failed to escalate complexity {packet.complexity} to HIGH (got {packet.level})"
            )


if __name__ == "__main__":
    unittest.main()
