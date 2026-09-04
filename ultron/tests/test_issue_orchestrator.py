import os
import unittest
import tempfile

from ultron.core.issue_orchestrator import IssueOrchestrator
from ultron.core.issue_memory import IssueRecord

class TestIssueOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orchestrator = IssueOrchestrator(self.temp_dir.name)

        # Seed an issue
        self.issue = IssueRecord(
            issue_id="BUG-ORCH-01",
            pillar="FUNCTIONAL",
            component="calculator",
            target="calc.py",
            failure_class="DIVISION_BY_ZERO",
            symptom="ZeroDivisionError when denominator is zero",
            reproduction="calc(10, 0)",
            reproduction_signature="ZERO_DIV_CALC",
            fingerprint="",
            root_cause="Missing zero check in denominator",
            status="DISCOVERED"
        )
        self.orchestrator.issue_memory.record_issue(self.issue)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_complete_9_phase_orchestration_loop(self):
        # 1. Discover & Prioritize
        discovered = self.orchestrator.discover_issues()
        self.assertGreaterEqual(len(discovered), 1)

        # 2. Select Issue
        s_sel = self.orchestrator.select_issue("BUG-ORCH-01")
        self.assertEqual(s_sel.status, "ISSUE_SELECTED")
        self.assertEqual(s_sel.active_issue, "BUG-ORCH-01")

        # 3. Compile Mission
        mission = self.orchestrator.compile_mission("BUG-ORCH-01")
        self.assertIn("xml_envelope", mission)
        st = self.orchestrator.work_queue.get_state()
        self.assertEqual(st.status, "MISSION_READY")

        # 4. Execute Attempt
        attempt = self.orchestrator.execute_attempt(modified_files=["calc.py"])
        self.assertEqual(attempt.changed_files, ["calc.py"])
        self.assertEqual(attempt.unexpected_files, [])

        # 5. Observe State
        observed = self.orchestrator.observe_state(
            snapshot_id="snap_v1",
            test_results={"passed": True, "passed_count": 5, "failed_count": 0},
            visual_snapshot={"runtime_health": {"status": "HEALTHY"}, "action_priority_conflicts": []}
        )
        self.assertEqual(observed.snapshot_after, "snap_v1")

        # 6. Verify Attempt (Three Pillars)
        is_verified, reasons = self.orchestrator.verify_attempt()
        self.assertTrue(is_verified, f"Failed verification: {reasons}")
        self.assertTrue(observed.three_pillar_results["FUNCTIONAL"])
        self.assertTrue(observed.three_pillar_results["CONNECTIVITY"])
        self.assertTrue(observed.three_pillar_results["HUMAN"])

        # 7. Guard Regression & Advance
        s_ready = self.orchestrator.guard_regression_and_advance()
        self.assertEqual(s_ready.status, "CHECKPOINT_READY")

        # 8. Checkpoint Progression
        cid = self.orchestrator.checkpoint_progression("Fixed division by zero error")
        self.assertTrue(cid.startswith("CHK-"))
        st_final = self.orchestrator.work_queue.get_state()
        self.assertEqual(st_final.status, "CHECKPOINTED")

        # 9. Verify Issue is guarded in IssueMemory
        saved_iss = self.orchestrator.issue_memory.get_issue("BUG-ORCH-01")
        self.assertEqual(saved_iss.status, "REGRESSION_GUARD")
        self.assertIn(cid, saved_iss.checkpoints)

    def test_unexpected_files_trigger_blocked_state(self):
        self.orchestrator.select_issue("BUG-ORCH-01")
        self.orchestrator.compile_mission("BUG-ORCH-01")

        # Simulate agent touching forbidden file outside declared targets
        self.orchestrator.execute_attempt(modified_files=["calc.py", "unauthorized_secret.py"])
        self.orchestrator.observe_state(
            snapshot_id="snap_v2",
            test_results={"passed": True, "passed_count": 5, "failed_count": 0}
        )

        st = self.orchestrator.guard_regression_and_advance()
        self.assertEqual(st.status, "BLOCKED")
        self.assertTrue(len(st.blocking_reasons) > 0)

if __name__ == "__main__":
    unittest.main()
