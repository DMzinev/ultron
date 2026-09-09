"""
ultron/tests/test_self_scan_integrity.py

Automated structural invariant test suite for Task P2-A3 per docs/AGENT_EXECUTION_PLAN_PHASE2.md:
"Reconcile the Self-Scan File Count Discrepancy (71 vs. 148)"

Asserts:
1. Zero test/fixture contamination: analyzer.analyze_directory excludes ultron/tests and ultron/tests/fixtures.
2. Complete partition of git-tracked Python files: P_prod (analyzed) and P_tests (tests + fixtures) are disjoint
   and sum exactly to the total tracked Python files.
3. Risk evaluation honesty: The self-scan denominator is 100% production code, with HIGH files <= 15.0%.
"""

import os
import sys
import shutil
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ultron.core import analyzer
from ultron.interfaces.cli.commands.gate import extract_current_analysis


class TestSelfScanIntegrity(unittest.TestCase):
    """Verifies that self-scan operates strictly on production code without fixture dilution."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = REPO_ROOT
        cls.codebase = analyzer.analyze_directory(cls.repo_root)

    def test_self_scan_excludes_tests_and_fixtures(self):
        """Invariant: analyze_directory('.') must contain ZERO files from tests/ or fixtures/."""
        scanned_files = list(self.codebase.keys())
        self.assertGreaterEqual(
            len(scanned_files), 71,
            f"Expected at least 71 production files (baseline), got {len(scanned_files)}"
        )

        test_leaks = [f for f in scanned_files if "tests/" in f.replace("\\", "/")]
        self.assertEqual(
            test_leaks, [],
            f"Test files leaked into analyze_directory codebase: {test_leaks}"
        )

        fixture_leaks = [f for f in scanned_files if "fixtures/" in f.replace("\\", "/")]
        self.assertEqual(
            fixture_leaks, [],
            f"Fixture files leaked into analyze_directory codebase: {fixture_leaks}"
        )

    def test_self_scan_partition_invariants(self):
        """
        Invariant: The set of tracked Python files must partition cleanly into:
          P_prod (scanned by analyzer) + P_tests (ultron/tests/*) = All Tracked Files
        with strict disjointness: P_prod ∩ P_tests = ∅.
        """
        if not shutil.which("git"):
            self.skipTest("git executable not found in PATH")

        try:
            res = subprocess.run(
                ["git", "ls-files", "--", "*.py"],
                cwd=self.repo_root,
                capture_output=True,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode != 0:
                self.skipTest("Failed to execute git ls-files")
            tracked_files = [f.strip().replace("\\", "/") for f in res.stdout.splitlines() if f.strip()]
        except Exception as e:
            self.skipTest(f"Git execution failed: {e}")

        prod_files = set(f.replace("\\", "/") for f in self.codebase.keys())
        test_files = set(f for f in tracked_files if f.startswith("ultron/tests/"))
        fixture_files = set(f for f in tracked_files if f.startswith("ultron/tests/fixtures/"))
        agent_files = set(f for f in tracked_files if f.startswith(".agents/"))

        # Invariant 1: Fixtures are strictly a subset of tests
        self.assertTrue(
            fixture_files.issubset(test_files),
            "All fixtures must reside within ultron/tests/"
        )

        # Invariant 2: Disjointness — prod files, test files, and agent files have empty mutual intersections
        intersection = prod_files.intersection(test_files)
        self.assertEqual(
            intersection, set(),
            f"Found test files intersecting with production codebase: {intersection}"
        )
        agent_prod_intersection = prod_files.intersection(agent_files)
        self.assertEqual(
            agent_prod_intersection, set(),
            f"Found agent files intersecting with production codebase: {agent_prod_intersection}"
        )
        agent_test_intersection = test_files.intersection(agent_files)
        self.assertEqual(
            agent_test_intersection, set(),
            f"Found agent files intersecting with test files: {agent_test_intersection}"
        )

        # Invariant 3: Zero fixture contamination in prod
        fixture_intersection = prod_files.intersection(fixture_files)
        self.assertEqual(
            fixture_intersection, set(),
            f"Found fixture files intersecting with production codebase: {fixture_intersection}"
        )

        # Invariant 4: Complete partition
        partitioned = prod_files.union(test_files).union(agent_files)
        unaccounted = set(tracked_files) - partitioned
        self.assertEqual(
            unaccounted, set(),
            f"Tracked Python files not accounted for in partition: {unaccounted}"
        )
        self.assertEqual(
            len(prod_files) + len(test_files) + len(agent_files), len(tracked_files),
            "Sum of prod files, test files, and agent files must exactly equal total tracked Python files"
        )

    def test_self_scan_risk_distribution_honesty(self):
        """
        Invariant: Risk scoring on self-scan evaluates 100% production files.
        HIGH risk ratio must not exceed the 15.0% ceiling.
        """
        analysis = extract_current_analysis(self.repo_root)
        self.assertGreater(analysis["total_files"], 0)
        self.assertEqual(analysis["total_files"], len(self.codebase))

        high_risks = [r for r in analysis["risks"] if r.get("level") == "HIGH"]
        high_count = len(high_risks)
        high_pct = (high_count / analysis["total_files"]) * 100.0

        # Max allowed ceiling: 15%
        self.assertLessEqual(
            high_pct, 15.0,
            f"HIGH risk percentage ({high_pct:.2f}%) exceeded 15.0% ceiling ({high_count}/{analysis['total_files']})"
        )


if __name__ == "__main__":
    unittest.main()
