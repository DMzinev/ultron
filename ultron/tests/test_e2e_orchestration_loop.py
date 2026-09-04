"""
ultron.tests.test_e2e_orchestration_loop
The Ultimate Acceptance Test for Phase 1.6:
Validates that Ultron can coordinate the complete development lifecycle:
1. Happy Path: Discover -> Select -> Compile Mission -> Implement -> Observe Reality -> Verify Three Pillars -> Checkpoint -> Guard -> Next Issue.
2. Adversarial Path: Intentional Bad Change -> Detect Failure -> Repair Mission Compiled -> Fix Implemented -> Verified Clean.
"""

import os
import sys
import unittest
import tempfile
import time
from typing import Dict, Any

from ultron.core.issue_orchestrator import IssueOrchestrator
from ultron.core.issue_memory import IssueRecord
from ultron.core.work_queue import WorkQueue


class TestE2EOrchestrationLoop(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = self.temp_dir.name
        self.orchestrator = IssueOrchestrator(self.repo_root)

        # Create a sample source file
        self.calc_file = os.path.join(self.repo_root, "calculator.py")
        with open(self.calc_file, "w", encoding="utf-8") as f:
            f.write("def compute_margin(rev, cost):\n    return rev - cost\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_happy_path_orchestration_to_checkpoint_and_guard(self):
        """
        Tests complete continuous cycle:
        DISCOVER -> SELECT -> COMPILE -> ATTEMPT -> OBSERVE -> VERIFY -> GUARD -> CHECKPOINT -> NEXT
        """
        # 1. Seed discovered issue
        issue = IssueRecord(
            issue_id="BUG-E2E-01",
            pillar="FUNCTIONAL",
            component="calculator",
            target="calculator.py",
            failure_class="OFF_BY_ONE",
            symptom="Incorrect margin formula",
            reproduction="compute_margin(10, 5) != 5",
            reproduction_signature="SIG_OFF_BY_ONE_MARGIN",
            fingerprint="",
            root_cause="Subtracted wrong operand",
            status="DISCOVERED"
        )
        self.orchestrator.issue_memory.record_issue(issue)

        # 2. Discover & Prioritize
        issues = self.orchestrator.discover_issues()
        self.assertTrue(any(i.issue_id == "BUG-E2E-01" for i in issues))

        # 3. Select Issue
        state = self.orchestrator.select_issue("BUG-E2E-01")
        self.assertEqual(state.status, "ISSUE_SELECTED")
        self.assertEqual(state.active_issue, "BUG-E2E-01")

        # 4. Compile Mission
        mission = self.orchestrator.compile_mission("BUG-E2E-01")
        self.assertIn("xml_envelope", mission)
        self.assertEqual(self.orchestrator.work_queue.get_state().status, "MISSION_READY")

        # 5. Agent Implements
        with open(self.calc_file, "w", encoding="utf-8") as f:
            f.write("def compute_margin(rev, cost):\n    return max(0, rev - cost)\n")

        attempt = self.orchestrator.execute_attempt(modified_files=["calculator.py"])
        self.assertEqual(attempt.changed_files, ["calculator.py"])
        self.assertEqual(attempt.unexpected_files, [])

        # 6. Observe Reality (Tests + Browser Snapshot)
        observed = self.orchestrator.observe_state(
            snapshot_id="snap_e2e_v1",
            test_results={"passed": True, "passed_count": 10, "failed_count": 0},
            visual_snapshot={
                "runtime_health": {"status": "HEALTHY"},
                "action_priority_conflicts": []
            }
        )
        self.assertEqual(observed.snapshot_after, "snap_e2e_v1")

        # 7. Three-Pillar Verification
        is_verified, reasons = self.orchestrator.verify_attempt()
        self.assertTrue(is_verified, f"Verification failed: {reasons}")
        self.assertTrue(observed.three_pillar_results["FUNCTIONAL"])
        self.assertTrue(observed.three_pillar_results["CONNECTIVITY"])
        self.assertTrue(observed.three_pillar_results["HUMAN"])

        # 8. Guard Regression & Advance
        state_ready = self.orchestrator.guard_regression_and_advance()
        self.assertEqual(state_ready.status, "CHECKPOINT_READY")

        # 9. Checkpoint Progression
        cid = self.orchestrator.checkpoint_progression("Fixed compute_margin logic")
        self.assertTrue(cid.startswith("CHK-"))
        self.assertEqual(self.orchestrator.work_queue.get_state().status, "CHECKPOINTED")

        # 10. Issue Closed & Guard Active
        saved_iss = self.orchestrator.issue_memory.get_issue("BUG-E2E-01")
        self.assertEqual(saved_iss.status, "REGRESSION_GUARD")
        self.assertIn(cid, saved_iss.checkpoints)

    def test_adversarial_bad_change_and_repair_loop(self):
        """
        Adversarial Test:
        Intentional Bad Change -> Detect Failure -> Route to REPAIR_REQUIRED -> Fix -> Verify
        """
        issue = IssueRecord(
            issue_id="BUG-E2E-02",
            pillar="FUNCTIONAL",
            component="calculator",
            target="calculator.py",
            failure_class="ACCURACY",
            symptom="Precision loss",
            reproduction="float div error",
            reproduction_signature="PRECISION_LOSS_SIG",
            fingerprint="",
            root_cause="Using int instead of float",
            status="DISCOVERED"
        )
        self.orchestrator.issue_memory.record_issue(issue)

        self.orchestrator.select_issue("BUG-E2E-02")
        self.orchestrator.compile_mission("BUG-E2E-02")

        # Simulate Agent introducing a failing change (e.g. syntax error or test failure)
        self.orchestrator.execute_attempt(modified_files=["calculator.py"])
        self.orchestrator.observe_state(
            snapshot_id="snap_bad_v1",
            test_results={"passed": False, "passed_count": 8, "failed_count": 2},
            visual_snapshot={"runtime_health": {"status": "HEALTHY"}, "action_priority_conflicts": []}
        )

        # Verification must FAIL
        is_verified, reasons = self.orchestrator.verify_attempt()
        self.assertFalse(is_verified)
        self.assertIn("Functional Pillar Failed: Tests failing or unexecuted.", reasons)

        # State advance must route to REPAIR_REQUIRED (NOT Checkpoint Ready)
        state_repair = self.orchestrator.guard_regression_and_advance()
        self.assertEqual(state_repair.status, "REPAIR_REQUIRED")
        self.assertTrue(len(state_repair.blocking_reasons) > 0)

        # Agent repairs the code
        self.orchestrator.execute_attempt(modified_files=["calculator.py"])
        self.orchestrator.observe_state(
            snapshot_id="snap_fixed_v2",
            test_results={"passed": True, "passed_count": 10, "failed_count": 0},
            visual_snapshot={"runtime_health": {"status": "HEALTHY"}, "action_priority_conflicts": []}
        )

        is_verified_now, _ = self.orchestrator.verify_attempt()
        self.assertTrue(is_verified_now)
        state_ready_now = self.orchestrator.guard_regression_and_advance()
        self.assertEqual(state_ready_now.status, "CHECKPOINT_READY")

    def test_multi_iteration_continuous_loop_with_historical_regression_reopening(self):
        """
        Phase 1.7 Definition of Done:
        Issue 1 -> Mission -> Fix -> Verify -> Checkpoint
        Issue 2 -> Mission -> Fix -> Verify -> Checkpoint
        Historical Regression Injected -> Detect -> Auto-reopen Issue 1 -> Blocked -> Repair -> Checkpoint
        """
        from ultron.core.models import build_snapshot_id

        # -------------------------------------------------------------
        # Iteration 1: Issue 1 (Tax Calculation)
        # -------------------------------------------------------------
        issue1 = IssueRecord(
            issue_id="BUG-TAX-01",
            pillar="FUNCTIONAL",
            component="calculator",
            target="calculator.py",
            failure_class="TAX_ROUNDING",
            symptom="Tax rounding truncation",
            reproduction="calc_tax(100) == 0",
            reproduction_signature="TAX_SIG_ERR_TRUNC",
            fingerprint="",
            root_cause="Integer division in tax helper",
            status="DISCOVERED"
        )
        self.orchestrator.issue_memory.record_issue(issue1)
        self.orchestrator.select_issue("BUG-TAX-01")
        self.orchestrator.compile_mission("BUG-TAX-01")

        with open(self.calc_file, "a", encoding="utf-8") as f:
            f.write("\ndef calc_tax(v):\n    return v * 0.1\n")

        self.orchestrator.execute_attempt(modified_files=["calculator.py"])
        snap1 = build_snapshot_id("hash_tax_v1")
        self.orchestrator.observe_state(
            snapshot_id=snap1,
            test_results={"passed": True, "passed_count": 5, "failed_count": 0},
            visual_snapshot={"runtime_health": {"status": "HEALTHY"}, "action_priority_conflicts": []}
        )
        is_ver1, _ = self.orchestrator.verify_attempt()
        self.assertTrue(is_ver1)
        self.orchestrator.guard_regression_and_advance()
        chk1 = self.orchestrator.checkpoint_progression("Resolved BUG-TAX-01")
        self.assertEqual(self.orchestrator.issue_memory.get_issue("BUG-TAX-01").status, "REGRESSION_GUARD")

        # -------------------------------------------------------------
        # Iteration 2: Issue 2 (Discount Logic)
        # -------------------------------------------------------------
        issue2 = IssueRecord(
            issue_id="BUG-DISC-02",
            pillar="FUNCTIONAL",
            component="calculator",
            target="calculator.py",
            failure_class="DISCOUNT_BOUND",
            symptom="Negative discount allowed",
            reproduction="apply_disc(100, -10)",
            reproduction_signature="DISC_SIG_NEG",
            fingerprint="",
            root_cause="Missing boundary check",
            status="DISCOVERED"
        )
        self.orchestrator.issue_memory.record_issue(issue2)
        self.orchestrator.discover_issues()
        self.orchestrator.select_issue("BUG-DISC-02")
        self.orchestrator.compile_mission("BUG-DISC-02")

        with open(self.calc_file, "a", encoding="utf-8") as f:
            f.write("\ndef apply_disc(v, d):\n    return v - max(0, d)\n")

        self.orchestrator.execute_attempt(modified_files=["calculator.py"])
        snap2 = build_snapshot_id("hash_disc_v2")
        self.orchestrator.observe_state(
            snapshot_id=snap2,
            test_results={"passed": True, "passed_count": 7, "failed_count": 0},
            visual_snapshot={"runtime_health": {"status": "HEALTHY"}, "action_priority_conflicts": []}
        )
        is_ver2, _ = self.orchestrator.verify_attempt()
        self.assertTrue(is_ver2)
        self.orchestrator.guard_regression_and_advance()
        chk2 = self.orchestrator.checkpoint_progression("Resolved BUG-DISC-02")
        self.assertEqual(self.orchestrator.issue_memory.get_issue("BUG-DISC-02").status, "REGRESSION_GUARD")

        # -------------------------------------------------------------
        # Iteration 3: Injected Historical Regression of Issue 1
        # -------------------------------------------------------------
        # Re-inject the tax truncation bug
        with open(self.calc_file, "w", encoding="utf-8") as f:
            f.write("def calc_tax(v):\n    return int(v / 1000)  # Broken regression\n")

        # Try to execute an attempt on calculator.py
        self.orchestrator.work_queue.transition_to("DISCOVERING")
        self.orchestrator.work_queue.transition_to("ISSUE_SELECTED", context={"active_issue": "BUG-DISC-02"})
        self.orchestrator.work_queue.transition_to("MISSION_READY")
        self.orchestrator.execute_attempt(modified_files=["calculator.py"])

        # Test results report the failure matching BUG-TAX-01's reproduction signature
        self.orchestrator.observe_state(
            snapshot_id="snap_regression",
            test_results={
                "passed": False,
                "passed_count": 5,
                "failed_count": 1,
                "failures": "AssertionError: TAX_SIG_ERR_TRUNC tax rounding failed"
            },
            visual_snapshot={"runtime_health": {"status": "HEALTHY"}, "action_priority_conflicts": []}
        )

        # Verification must detect historical regression!
        is_ver_reg, reg_reasons = self.orchestrator.verify_attempt()
        self.assertFalse(is_ver_reg)
        self.assertTrue(any("Historical issue 'BUG-TAX-01' re-manifested" in r for r in reg_reasons))

        # Advance must route to BLOCKED
        state_blocked = self.orchestrator.guard_regression_and_advance()
        self.assertEqual(state_blocked.status, "BLOCKED")

        # Historical issue BUG-TAX-01 must be REOPENED in memory
        reopened_issue = self.orchestrator.issue_memory.get_issue("BUG-TAX-01")
        self.assertEqual(reopened_issue.status, "REOPENED")


if __name__ == "__main__":
    unittest.main()

