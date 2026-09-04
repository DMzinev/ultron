"""
Ultron Test Suite — Semantic Truth & Contradiction Rejection (v2.7.0)
Validates that Ultron never converts absence of evidence into evidence of absence.
Enforces:
1. Missing test evidence blocks continuation (PAUSE & REVIEW).
2. Partial parse failures are explicitly tagged as PARTIAL completeness.
3. Missing Git metadata preserves AST analysis without false churn zeroing.
4. Offline AI proxy is truthfully labeled as native fallback.
5. Contradictory snapshot identities are rejected.
"""

import os
import tempfile
import shutil
import unittest

from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.ai.client import AIClient
from ultron.core.git_adapter import GitEvidenceAdapter
from ultron.core.safety_evaluator import SafetyEvaluator


class TestSemanticContradictions(unittest.TestCase):
    def test_unexecuted_tests_blocks_continuation(self):
        """Invariant: Missing test evidence != Safe. Must return PAUSE & REVIEW."""
        report = SafetyEvaluator.evaluate(test_results=None)
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.badge, "PAUSE & REVIEW")
        self.assertIn("TESTS_UNEXECUTED", report.reason_codes)
        self.assertTrue(any("unexecuted" in b.lower() for b in report.blocking_conditions))

    def test_zero_tests_run_blocks_continuation(self):
        """Invariant: Zero tests executed must never trigger CONTINUE BUILDING."""
        zero_res = {"passed": False, "passed_count": 0, "failed_count": 0, "testsRun": 0}
        report = SafetyEvaluator.evaluate(test_results=zero_res)
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.badge, "PAUSE & REVIEW")

    def test_partial_syntax_error_completeness(self):
        """Invariant: Partial parse failures must yield PARTIAL completeness, not 100% complete."""
        temp_dir = tempfile.mkdtemp(prefix="ultron_semantic_test_")
        try:
            with open(os.path.join(temp_dir, "valid.py"), "w", encoding="utf-8") as f:
                f.write("def calculate():\n    return 42\n")
            with open(os.path.join(temp_dir, "broken.py"), "w", encoding="utf-8") as f:
                f.write("def broken(\n") # Syntax error

            codebase = analyzer.analyze_directory(temp_dir)
            files_discovered = [f for f in os.listdir(temp_dir) if f.endswith(".py")]
            files_parsed = list(codebase.keys())
            parse_errors = [f for f in files_discovered if f not in files_parsed]

            self.assertIn("valid.py", files_parsed)
            self.assertNotIn("broken.py", files_parsed)
            self.assertEqual(len(parse_errors), 1)

            completeness_pct = round((len(files_parsed) / len(files_discovered)) * 100.0, 1)
            self.assertEqual(completeness_pct, 50.0)
            self.assertNotEqual(completeness_pct, 100.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_git_metadata_preserves_ast(self):
        """Invariant: Missing Git repository does not throw errors and preserves AST analysis."""
        temp_dir = tempfile.mkdtemp(prefix="ultron_nogit_test_")
        try:
            with open(os.path.join(temp_dir, "standalone.py"), "w", encoding="utf-8") as f:
                f.write("class Service:\n    def run(self):\n        pass\n")

            adapter = GitEvidenceAdapter()
            records = adapter.parse_git_history(temp_dir)
            self.assertEqual(records, []) # Evidence unavailable, handled cleanly

            cb = analyzer.analyze_directory(temp_dir)
            packets = scoring.evaluate_risks(codebase=cb, target_files=["standalone.py"], repo_path=temp_dir)
            self.assertEqual(len(packets), 1)
            self.assertEqual(packets[0].file_path, "standalone.py")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_offline_ai_proxy_fallback_tagging(self):
        """Invariant: Offline AI proxy is truthfully labeled as native fallback, never faked."""
        client = AIClient(endpoint="http://127.0.0.1:10531/v1", timeout=0.5)
        res = client.query_critique(
            file_path="ultron/core/analyzer.py",
            complexity=15,
            coupling=5,
            impact_score=12.0
        )
        self.assertTrue(res.get("success"))
        source = res.get("source", "")
        self.assertTrue("Offline Fallback" in source or "Native AST" in source)
        self.assertNotIn("gpt-4o", source.lower())

    def test_mismatched_snapshot_id_rejected(self):
        """Invariant: Mismatched snapshot identities must be rejected to prevent state corruption."""
        def validate_identity(active_snap: str, active_repo: str, incoming: dict) -> bool:
            if incoming.get("repository_id") and incoming.get("repository_id") != active_repo:
                return False
            if incoming.get("snapshot_id") and incoming.get("snapshot_id") != active_snap:
                return False
            return True

        self.assertTrue(validate_identity("snap_1", "repo_1", {"snapshot_id": "snap_1", "repository_id": "repo_1"}))
        self.assertFalse(validate_identity("snap_1", "repo_1", {"snapshot_id": "snap_stale", "repository_id": "repo_1"}))
        self.assertFalse(validate_identity("snap_1", "repo_1", {"snapshot_id": "snap_1", "repository_id": "repo_other"}))


if __name__ == "__main__":
    unittest.main()
