"""
ultron/tests/test_skip_invariants.py

Automated invariant test suite for Task P3-A2 per docs/AGENT_EXECUTION_PLAN_PHASE3.md:
"Stabilize and Document the Skipped-Test Count"

Asserts:
1. TestTrayLauncher in test_launchers.py declares exactly 9 test methods and is never skipped (runs via headless mocking).
2. test_cold_clean_machine_install_under_60s skips cleanly in isolation when network is simulated offline (producing the 10th skip).
3. AST static analysis across all test_*.py files asserts that only authorized, documented skips exist in the repository.
"""

import ast
import os
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TESTS_DIR = os.path.join(REPO_ROOT, "ultron", "tests")


class TestSkipInvariants(unittest.TestCase):
    """Hermetic invariant tests enforcing deterministic skip counts and inventory compliance."""

    def test_tray_launcher_skip_invariant(self):
        """Verify TestTrayLauncher declares exactly 9 test methods and is never skipped under headless mode."""
        from ultron.tests import test_launchers

        tray_cls = getattr(test_launchers, "TestTrayLauncher", None)
        self.assertIsNotNone(tray_cls, "TestTrayLauncher not found in test_launchers.py")

        test_methods = [m for m in dir(tray_cls) if m.startswith("test_")]
        self.assertEqual(
            len(test_methods),
            9,
            f"Expected exactly 9 test methods on TestTrayLauncher, found {len(test_methods)}: {test_methods}",
        )

        is_skipped = getattr(tray_cls, "__unittest_skip__", False)
        self.assertFalse(
            is_skipped,
            "TestTrayLauncher must have __unittest_skip__ == False under headless fallback mode",
        )

    def test_offline_network_skip_behavior(self):
        """Verify test_cold_clean_machine_install_under_60s produces a clean skip when network is unreachable."""
        from ultron.tests.test_install_first_run import TestInstallFirstRun

        suite = unittest.TestSuite()
        suite.addTest(TestInstallFirstRun("test_cold_clean_machine_install_under_60s"))

        result = unittest.TestResult()
        with patch("socket.create_connection", side_effect=OSError("Network probe simulated offline")):
            suite.run(result)

        self.assertEqual(len(result.failures), 0, "Offline simulation should not fail")
        self.assertEqual(len(result.errors), 0, "Offline simulation should not error")
        self.assertEqual(len(result.skipped), 1, "Offline simulation must produce exactly 1 skip")
        skip_reason = result.skipped[0][1]
        self.assertIn("pypi.org unreachable", skip_reason.lower())

    def test_authorized_skip_inventory_ast(self):
        """Statically inspect all test_*.py ASTs to assert that no undocumented skips exist in the repository."""
        authorized_skips = {
            # file_basename -> set of authorized functions/classes
            "test_install_first_run.py": {"test_cold_clean_machine_install_under_60s"},
            "test_openai_plan_reviewer.py": {"TestOpenAIPlanReviewer"},
            "test_recommendation_engine.py": {
                "test_role1_ranking_correctness_requests",
                "test_role3_category_isolation_bottle",
            },
            "test_self_scan_integrity.py": {"test_self_scan_partition_invariants"},
            "test_verify_command.py": {"test_verify_command_detects_skipped_test", "_SampleSkippedTest"},
        }

        test_files = [
            f for f in os.listdir(TESTS_DIR)
            if f.startswith("test_") and f.endswith(".py")
        ]

        found_skips = {}

        for fname in test_files:
            fpath = os.path.join(TESTS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as py_file:
                try:
                    tree = ast.parse(py_file.read(), filename=fname)
                except SyntaxError:
                    continue

            file_skips = set()

            for node in ast.walk(tree):
                # Check class or function decorators
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    for dec in node.decorator_list:
                        dec_name = ""
                        if isinstance(dec, ast.Attribute):
                            dec_name = dec.attr
                        elif isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Attribute):
                                dec_name = dec.func.attr
                            elif isinstance(dec.func, ast.Name):
                                dec_name = dec.func.id

                        if dec_name in ("skip", "skipIf", "skipUnless"):
                            file_skips.add(node.name)

                # Check self.skipTest calls inside function bodies
                if isinstance(node, ast.FunctionDef):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                            if child.func.attr == "skipTest":
                                file_skips.add(node.name)

            if file_skips:
                found_skips[fname] = file_skips

        # Compare found skips against authorized inventory
        for fname, skips in found_skips.items():
            self.assertIn(
                fname,
                authorized_skips,
                f"Unexpected skip detected in undeclared test file '{fname}': {skips}",
            )
            unauthorized = skips - authorized_skips[fname]
            self.assertEqual(
                len(unauthorized),
                0,
                f"Unauthorized skips detected in '{fname}': {unauthorized}. Allowed: {authorized_skips[fname]}",
            )


if __name__ == "__main__":
    unittest.main()
