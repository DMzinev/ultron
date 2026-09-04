import os
import sys
import unittest
import tempfile

from ultron.core.issue_memory import IssueMemory, IssueRecord
from ultron.core.safety_evaluator import SafetyEvaluator

class TestIssueMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = IssueMemory(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_get_issue(self):
        issue = IssueRecord(
            issue_id="ISSUE-TEST-01",
            pillar="CONNECTIVITY",
            component="router",
            target="/api/v1/test",
            failure_class="DISPATCH_FAIL",
            symptom="Endpoint returned 404",
            reproduction="curl http://localhost:8000/api/v1/test",
            reproduction_signature="SIG_DISPATCH_FAIL",
            fingerprint="",
            root_cause="Missing route registration",
            status="DISCOVERED"
        )
        self.memory.record_issue(issue)
        retrieved = self.memory.get_issue("ISSUE-TEST-01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.issue_id, "ISSUE-TEST-01")
        self.assertEqual(retrieved.pillar, "CONNECTIVITY")
        self.assertTrue(len(retrieved.fingerprint) == 16)

    def test_mark_resolved_creates_regression_guard(self):
        issue = IssueRecord(
            issue_id="ISSUE-TEST-02",
            pillar="FUNCTIONAL",
            component="math_engine",
            target="calc()",
            failure_class="OFF_BY_ONE",
            symptom="Off by one error in margin",
            reproduction="calc(10, 5) returned 4 instead of 5",
            reproduction_signature="MARGIN_OFF_BY_ONE",
            fingerprint="",
            root_cause="Subtracted 1 too many",
            status="DISCOVERED"
        )
        self.memory.record_issue(issue)
        resolved = self.memory.mark_resolved("ISSUE-TEST-02", "Fixed index formula", "test_margin_parity")
        self.assertEqual(resolved.status, "REGRESSION_GUARD")
        self.assertIsNotNone(resolved.resolved_at)

    def test_detect_regression_triggers_reopen_and_blocks_safety_gate(self):
        # 1. Create and resolve issue under regression guard
        issue = IssueRecord(
            issue_id="ISSUE-GUARDED",
            pillar="FUNCTIONAL",
            component="compiler",
            target="compiler.py::build",
            failure_class="CONTRADICTION",
            symptom="Target matches forbidden path",
            reproduction="build(['a.py'], ['a.py'])",
            reproduction_signature="TARGET_MATCHES_FORBIDDEN",
            fingerprint="",
            root_cause="Contradiction check omitted",
            status="REGRESSION_GUARD"
        )
        self.memory.record_issue(issue)

        # 2. Check for regression with exact same signature
        regressed = self.memory.check_for_regression(
            pillar="FUNCTIONAL",
            component="compiler",
            target="compiler.py::build",
            failure_class="CONTRADICTION",
            reproduction_signature="TARGET_MATCHES_FORBIDDEN"
        )
        self.assertIsNotNone(regressed)
        self.assertEqual(regressed.status, "REOPENED")

        # 3. SafetyEvaluator must block continuation when an issue is REOPENED
        report = SafetyEvaluator.evaluate(
            test_results={"passed": True, "passed_count": 10, "failed_count": 0},
            repo_root=self.temp_dir.name
        )
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.badge, "PAUSE & REVIEW")
        self.assertIn("REGRESSION_DETECTED", report.reason_codes)

if __name__ == "__main__":
    unittest.main()
