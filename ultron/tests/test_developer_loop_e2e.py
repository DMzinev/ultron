"""
Ultron End-to-End Developer Loop & Failure Recovery Test Suite
Validates the complete orchestration lifecycle:
CONNECT -> UNDERSTAND -> PLAN -> BUILD CONTEXT -> VERIFY -> CONTINUE
Including browser reload persistence, repository switching isolation, and failure recovery.
"""

import os
import shutil
import tempfile
import unittest

from ultron.core.objective_tracker import ObjectiveTracker
from ultron.core.agent_context_builder import AgentContextBuilder
from ultron.core.safety_evaluator import SafetyEvaluator


class TestDeveloperLoopE2E(unittest.TestCase):
    def setUp(self):
        self.repo_a = tempfile.mkdtemp(prefix="ultron_repo_a_")
        self.repo_b = tempfile.mkdtemp(prefix="ultron_repo_b_")

    def tearDown(self):
        for path in (self.repo_a, self.repo_b):
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)

    def test_complete_orchestration_developer_loop(self):
        """
        Step 1: CONNECT to Repo A
        Step 2: PLAN active objective with 3 tasks
        Step 3: Complete Task 1 -> auto-promote Task 2 to in_progress
        Step 4: RELOAD -> verify exact persistence from disk
        Step 5: SWITCH to Repo B -> verify complete isolation (no cross-repo state leak)
        Step 6: BUILD CONTEXT -> verify provider projections
        Step 7: VERIFY SAFETY -> verify safe-to-continue evaluator
        Step 8: CONTINUE -> complete Task 2 -> promote Task 3
        """
        # Step 1: Connect to Repo A
        tracker_a = ObjectiveTracker(self.repo_a)
        init_state = tracker_a.get_objective()
        self.assertEqual(init_state["repository_root"], os.path.normcase(os.path.abspath(self.repo_a)))

        # Step 2: Plan
        obj_a = tracker_a.set_objective(
            title="Implement User Authentication",
            description="Add JWT tokens, password hashing, and login routes.",
            tasks=[
                {"id": "task_1", "title": "Create user model", "status": "in_progress"},
                {"id": "task_2", "title": "Implement password hashing", "status": "pending"},
                {"id": "task_3", "title": "Add login API endpoint", "status": "pending"}
            ],
            constraints=["Do not modify payments", "Preserve existing user table schema"],
            acceptance=["All unit tests pass", "Zero unhandled exceptions"],
            affected_areas=["auth/user.py", "auth/jwt.py"]
        )
        self.assertEqual(obj_a["progress_pct"], 0.0)
        self.assertEqual(len(obj_a["tasks"]), 3)

        # Step 3: Complete Task 1
        step3_res = tracker_a.complete_task("task_1")
        self.assertTrue(step3_res["success"])
        state_after_t1 = step3_res["state"]
        self.assertEqual(state_after_t1["tasks"][0]["status"], "done")
        self.assertEqual(state_after_t1["tasks"][1]["status"], "in_progress")
        self.assertEqual(state_after_t1["progress_pct"], 33.3)

        # Step 4: Reload (simulating browser page refresh / session restart)
        reloaded_tracker_a = ObjectiveTracker(self.repo_a)
        reloaded_state_a = reloaded_tracker_a.get_objective()
        self.assertEqual(reloaded_state_a["title"], "Implement User Authentication")
        self.assertEqual(reloaded_state_a["progress_pct"], 33.3)
        self.assertEqual(reloaded_state_a["tasks"][0]["status"], "done")
        self.assertEqual(reloaded_state_a["tasks"][1]["status"], "in_progress")
        self.assertEqual(reloaded_state_a["tasks"][2]["status"], "pending")

        # Step 5: Switch to Repo B (verify complete repository isolation)
        tracker_b = ObjectiveTracker(self.repo_b)
        state_b = tracker_b.get_objective()
        self.assertNotEqual(state_b["repository_id"], reloaded_state_a["repository_id"])
        self.assertNotEqual(state_b["title"], "Implement User Authentication")
        self.assertEqual(state_b["title"], "Initial Repository Setup & Discovery")

        # Step 6: Build Context (Generate canonical context and provider projections)
        ctx = AgentContextBuilder.build(reloaded_state_a, repo_path=self.repo_a)
        self.assertEqual(ctx.objective_title, "Implement User Authentication")
        self.assertEqual(ctx.active_task["title"], "Implement password hashing")
        self.assertEqual(len(ctx.completed_tasks), 1)
        self.assertEqual(len(ctx.pending_tasks), 1)

        # Verify Claude, Cursor, Antigravity, and Aider renderings
        claude_prompt = AgentContextBuilder.render_claude(ctx)
        cursor_prompt = AgentContextBuilder.render_cursor(ctx)
        agy_prompt = AgentContextBuilder.render_antigravity(ctx)
        aider_prompt = AgentContextBuilder.render_aider(ctx)

        self.assertIn("Implement password hashing", claude_prompt)
        self.assertIn("Do not modify payments", cursor_prompt)
        self.assertIn("TARGET_OBJECTIVE: Implement User Authentication", agy_prompt)
        self.assertIn("/add auth/user.py", aider_prompt)

        # Step 7: Verify Safety
        # 7a. Passing tests -> CONTINUE BUILDING
        safe_res = SafetyEvaluator.evaluate(
            test_results={"passed": True, "passed_count": 50, "failed_count": 0},
            modified_files=["auth/user.py", "auth/jwt.py"],
            boundary_constraints=reloaded_state_a["constraints"],
            acceptance_criteria=reloaded_state_a["acceptance"]
        )
        self.assertTrue(safe_res.safe_to_continue)
        self.assertEqual(safe_res.badge, "CONTINUE BUILDING")

        # 7b. Boundary violation (modifying payments when forbidden) -> PAUSE & REVIEW
        violation_res = SafetyEvaluator.evaluate(
            test_results={"passed": True, "passed_count": 50, "failed_count": 0},
            modified_files=["payments/stripe_client.py"],
            boundary_constraints=reloaded_state_a["constraints"]
        )
        self.assertFalse(violation_res.safe_to_continue)
        self.assertEqual(violation_res.badge, "PAUSE & REVIEW")

        # Step 8: Continue (Complete Task 2 -> auto-promote Task 3)
        step8_res = reloaded_tracker_a.complete_task("task_2")
        self.assertTrue(step8_res["success"])
        state_after_t2 = step8_res["state"]
        self.assertEqual(state_after_t2["tasks"][1]["status"], "done")
        self.assertEqual(state_after_t2["tasks"][2]["status"], "in_progress")
        self.assertEqual(state_after_t2["progress_pct"], 66.7)

    def test_failure_recovery_on_corrupted_storage(self):
        """Ensures that corrupted objective JSON gracefully resets without raising an unhandled exception."""
        tracker = ObjectiveTracker(self.repo_a)
        storage_path = os.path.join(self.repo_a, ".ultron", "objective.json")
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        with open(storage_path, "w", encoding="utf-8") as f:
            f.write("<<< INVALID CORRUPTED DATA >>>")

        recovered = tracker.get_objective()
        self.assertIn("repository_id", recovered)
        self.assertIn("tasks", recovered)
        self.assertEqual(recovered["title"], "Initial Repository Setup & Discovery")

    def test_execution_reality_trace_continuity(self):
        """Phase 2.3: Verifies that ExecutionRealityTrace connects actions to outcomes across the control plane."""
        from ultron.core.development_session import ExecutionRealityTrace, DevelopmentAttempt
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.issue_memory import IssueRecord

        orch = IssueOrchestrator(self.repo_a)
        # Register an issue
        issue = IssueRecord(
            issue_id="ISSUE-TRACE-01",
            pillar="FUNCTIONAL",
            component="test_component",
            target="ultron/core/sample.py",
            failure_class="NULL_POINTER",
            symptom="Sample failed to initialize",
            reproduction="run sample init",
            reproduction_signature="SAMPLE_INIT_FAIL",
            root_cause="Missing configuration parameter"
        )
        orch.issue_memory.record_issue(issue)
        orch.select_issue(issue.issue_id)

        # Compile mission and verify trace attachment
        bundle = orch.compile_mission(issue.issue_id)
        self.assertIn("execution_reality_trace", bundle)
        trace = bundle["execution_reality_trace"]
        self.assertEqual(trace["state_before"], "ISSUE_SELECTED")
        self.assertEqual(trace["state_after"], "MISSION_READY")
        self.assertIn("Selected issue 'ISSUE-TRACE-01'", trace["trigger"])

        # Check work summary exposes trace
        summary = orch.get_current_work_summary()
        self.assertIn("execution_reality_trace", summary["work"])
        self.assertEqual(summary["work"]["execution_reality_trace"]["trace_id"], trace["trace_id"])

        # Check multi-provider prompt rendering includes trace
        ctx = AgentContextBuilder.build(
            objective_state={"title": "Fix sample", "tasks": []},
            repo_path=self.repo_a,
            execution_trace=trace
        )
        md_prompt = AgentContextBuilder.render_markdown(ctx)
        self.assertIn("Execution Reality Trace", md_prompt)
        self.assertIn(trace["trace_id"], md_prompt)

        claude_prompt = AgentContextBuilder.render_claude(ctx)
        self.assertIn("<execution_reality_trace", claude_prompt)
        self.assertIn(trace["trace_id"], claude_prompt)

        cursor_prompt = AgentContextBuilder.render_cursor(ctx)
        self.assertIn("REALITY TRACE", cursor_prompt)

        agy_prompt = AgentContextBuilder.render_antigravity(ctx)
        self.assertIn("[EXECUTION_REALITY_TRACE]", agy_prompt)

    def test_mahoraga_adaptive_parameter_mutations(self):
        """Phase 2.3: Verifies that IssueMemory Mahoraga adaptive mutations prevent regression evasion."""
        from ultron.core.issue_memory import IssueMemory, IssueRecord

        im = IssueMemory(self.repo_a)
        base_issue = IssueRecord(
            issue_id="GUARD-MAHORAGA-01",
            pillar="FUNCTIONAL",
            component="server",
            target="ultron/interfaces/server.py",
            failure_class="TIMEOUT",
            symptom="Endpoint timed out",
            reproduction="slow call",
            reproduction_signature="SERVER_TIMEOUT_SIG",
            status="REGRESSION_GUARD"
        )
        im.record_issue(base_issue)

        # Test adaptive mutations
        mutations = IssueMemory.generate_adaptive_mutations("ultron/interfaces/server.py")
        self.assertGreaterEqual(len(mutations), 5)

        for mut_path in mutations:
            base_issue.status = "REGRESSION_GUARD"
            im.record_issue(base_issue)
            detected = im.check_for_regression(
                pillar="FUNCTIONAL",
                component="server",
                target=mut_path,
                failure_class="TIMEOUT",
                reproduction_signature="SERVER_TIMEOUT_SIG"
            )
            self.assertIsNotNone(detected, f"Mahoraga mutation failed to detect regression for target: '{mut_path}'")
            self.assertEqual(detected.issue_id, "GUARD-MAHORAGA-01")


if __name__ == "__main__":
    unittest.main()
