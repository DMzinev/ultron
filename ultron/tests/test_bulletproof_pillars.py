"""
ultron.tests.test_bulletproof_pillars
Comprehensive test suite verifying the bulletproof Three-Pillar architecture:
1. Functional Pillar: Zero-config AST syntax & static import integrity fallback.
2. Functional Pillar: Deterministic syntax error detection with line numbers.
3. Connectivity Pillar: Scope boundary containment and 1-click expand/revert remedies.
4. Human Reality Pillar: Epistemic degraded wireframe gating on UI issues.
5. End-to-End Dummy-Proof Progression: Raw script folder without test setup completes smoothly.
"""

import os
import sys
import tempfile
import shutil
import unittest
from typing import Dict, Any

from ultron.core.issue_orchestrator import IssueOrchestrator
from ultron.core.development_session import DevelopmentAttempt


class TestBulletproofPillars(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_pillar_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_zero_config_ast_syntax_fallback(self):
        """
        Verify that a zero-config repository without a test runner
        passes the Functional Pillar via AST Syntax & Static Import verification.
        """
        # Create a simple Python script repository without tests or pytest
        main_py = os.path.join(self.test_dir, "main.py")
        with open(main_py, "w", encoding="utf-8") as f:
            f.write("import os\nimport sys\n\ndef run():\n    return 'success'\n")

        orchestrator = IssueOrchestrator(self.test_dir)
        orchestrator.active_attempt = DevelopmentAttempt(
            attempt_id="ATT-ZERO-CONFIG-01",
            issue_id="ISS-01",
            mission_id="MIS-01",
            attempt_number=1,
            target_files=["main.py"],
            changed_files=["main.py"],
            unexpected_files=[],
            snapshot_before="snap-01",
            snapshot_after="snap-02",
            tests_after={},  # 0 test runners executed
            visual_state_after={"browser_reality": "FULL", "snapshot_id": "snap-02", "runtime_health": {"status": "HEALTHY"}}
        )

        is_verified, reasons = orchestrator.verify_attempt()

        self.assertTrue(is_verified, f"Expected verified attempt, got reasons: {reasons}")
        self.assertTrue(orchestrator.active_attempt.three_pillar_results["FUNCTIONAL"])
        self.assertTrue(orchestrator.active_attempt.three_pillar_results["CONNECTIVITY"])
        self.assertTrue(orchestrator.active_attempt.three_pillar_results["HUMAN"])
        
        # Verify truthful ground truth telemetry
        t_after = orchestrator.active_attempt.tests_after
        self.assertTrue(t_after.get("ast_verified"))
        self.assertTrue(t_after.get("passed"))
        self.assertEqual(t_after.get("failed_count"), 0)
        self.assertEqual(t_after.get("passed_count"), 0)

    def test_02_syntax_error_deterministic_rejection(self):
        """
        Verify that a syntax error in modified files deterministically fails
        the Functional Pillar with line number information.
        """
        broken_py = os.path.join(self.test_dir, "broken.py")
        with open(broken_py, "w", encoding="utf-8") as f:
            f.write("def broken(\n    return 'unclosed paren'\n")

        orchestrator = IssueOrchestrator(self.test_dir)
        orchestrator.active_attempt = DevelopmentAttempt(
            attempt_id="ATT-SYNTAX-FAIL-01",
            issue_id="ISS-02",
            mission_id="MIS-02",
            attempt_number=1,
            target_files=["broken.py"],
            changed_files=["broken.py"],
            unexpected_files=[],
            snapshot_before="snap-01",
            snapshot_after="snap-02",
            tests_after={},
            visual_state_after={"browser_reality": "FULL", "snapshot_id": "snap-02", "runtime_health": {"status": "HEALTHY"}}
        )

        is_verified, reasons = orchestrator.verify_attempt()

        self.assertFalse(is_verified)
        self.assertFalse(orchestrator.active_attempt.three_pillar_results["FUNCTIONAL"])
        self.assertTrue(any("Syntax errors detected" in r for r in reasons))

    def test_03_connectivity_scope_boundary_containment_and_remedy(self):
        """
        Verify that out-of-scope files trigger Connectivity Pillar warnings
        and can be absorbed via scope expansion.
        """
        target_py = os.path.join(self.test_dir, "target.py")
        with open(target_py, "w", encoding="utf-8") as f:
            f.write("def target(): pass\n")

        unexp_py = os.path.join(self.test_dir, "unrelated.py")
        with open(unexp_py, "w", encoding="utf-8") as f:
            f.write("def unrelated(): pass\n")

        orchestrator = IssueOrchestrator(self.test_dir)
        orchestrator.active_attempt = DevelopmentAttempt(
            attempt_id="ATT-SCOPE-01",
            issue_id="ISS-03",
            mission_id="MIS-03",
            attempt_number=1,
            target_files=["target.py"],
            changed_files=["target.py", "unrelated.py"],
            unexpected_files=["unrelated.py"],
            snapshot_before="snap-01",
            snapshot_after="snap-02",
            tests_after={},
            visual_state_after={"browser_reality": "FULL", "snapshot_id": "snap-02", "runtime_health": {"status": "HEALTHY"}}
        )

        # 1. Verification fails due to unexpected files
        is_verified, reasons = orchestrator.verify_attempt()
        self.assertFalse(is_verified)
        self.assertFalse(orchestrator.active_attempt.three_pillar_results["CONNECTIVITY"])
        self.assertTrue(any("Unexpected files modified" in r for r in reasons))

        # 2. Apply 1-click scope expansion remedy
        orchestrator.active_attempt.target_files.append("unrelated.py")
        orchestrator.active_attempt.unexpected_files = []
        
        # 3. Re-verify: now passes
        is_verified_after, reasons_after = orchestrator.verify_attempt()
        self.assertTrue(is_verified_after, f"Expected pass after scope expansion, got: {reasons_after}")
        self.assertTrue(orchestrator.active_attempt.three_pillar_results["CONNECTIVITY"])

    def test_04_degraded_wireframe_blocks_ui_issue(self):
        """
        Verify that degraded wireframe evidence blocks Human Reality Pillar for UI issues.
        """
        web_file = os.path.join(self.test_dir, "web_app.js")
        with open(web_file, "w", encoding="utf-8") as f:
            f.write("console.log('ui script');\n")

        orchestrator = IssueOrchestrator(self.test_dir)
        orchestrator.active_attempt = DevelopmentAttempt(
            attempt_id="ATT-UI-01",
            issue_id="ISS-04",
            mission_id="MIS-04",
            attempt_number=1,
            target_files=["web_app.js"],
            changed_files=["web_app.js"],
            unexpected_files=[],
            snapshot_before="snap-01",
            snapshot_after="snap-02",
            tests_after={},
            visual_state_after={"browser_reality": "DEGRADED", "snapshot_id": "snap-02", "wireframe_fallback": True}
        )

        is_verified, reasons = orchestrator.verify_attempt()
        self.assertFalse(is_verified)
        self.assertFalse(orchestrator.active_attempt.three_pillar_results["HUMAN"])
        self.assertTrue(any("Degraded wireframe evidence" in r for r in reasons))

    def test_05_end_to_end_dummy_proof_lifecycle(self):
        """
        Verify complete 10-step lifecycle on a raw script folder without test setup:
        Connect -> Discover -> Select -> Compile -> Attempt -> Observe -> Verify -> Checkpoint
        """
        script_file = os.path.join(self.test_dir, "processor.py")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write("def process(items):\n    return [x * 2 for x in items]\n")

        orchestrator = IssueOrchestrator(self.test_dir)
        
        # Step 1: Discover issues
        issues = orchestrator.discover_issues()
        self.assertGreaterEqual(len(issues), 1)

        # Step 2: Prioritize
        queue = orchestrator.prioritize_issues()
        self.assertGreaterEqual(len(queue), 1)
        selected_id = queue[0].issue_id

        # Step 3: Select
        orchestrator.select_issue(selected_id)
        self.assertEqual(orchestrator.work_queue.get_state().status, "ISSUE_SELECTED")

        # Step 4: Compile Mission
        mission = orchestrator.compile_mission()
        self.assertIsNotNone(mission)
        self.assertEqual(orchestrator.work_queue.get_state().status, "MISSION_READY")

        # Step 5: Execute Attempt
        attempt = orchestrator.execute_attempt()
        self.assertIsNotNone(attempt)
        self.assertEqual(orchestrator.work_queue.get_state().status, "IMPLEMENTING")

        # Step 6: Observe State
        orchestrator.observe_state(
            snapshot_id="snap-proc-01",
            test_results={"passed": True, "passed_count": 0, "failed_count": 0, "ast_verified": True},
            visual_snapshot={"browser_reality": "FULL", "snapshot_id": "snap-proc-01", "runtime_health": {"status": "HEALTHY"}}
        )
        self.assertEqual(orchestrator.work_queue.get_state().status, "VERIFYING")

        # Step 7: Verify Attempt & Guard Regression
        state = orchestrator.guard_regression_and_advance()
        self.assertEqual(state.status, "CHECKPOINT_READY")

        # Step 8: Save Checkpoint
        cp = orchestrator.checkpoint_progression("Creator validated milestone")
        self.assertIsNotNone(cp)
        self.assertEqual(orchestrator.work_queue.get_state().status, "CHECKPOINTED")


if __name__ == "__main__":
    unittest.main()
