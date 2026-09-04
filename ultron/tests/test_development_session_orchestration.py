"""
Ultron Core — Development Session & Orchestration Loop Integration Test Suite (v2.6.3)
Validates the complete closed-loop orchestration cycle:
1. Connect -> 2. Plan -> 3. Session Start -> 4. Mission Envelope -> 5. Real Code Edit ->
6. Re-analyze -> 7. Snapshot Diff -> 8. Safety Gate -> 9. Task Advance -> 10. Next Mission ->
11. Failure / Blocker Path -> 12. State Continuity across Reloads & Repository Switching.
"""

import os
import json
import shutil
import tempfile
import unittest

from ultron.core import analyzer
from ultron.core.system_model import SystemModelManager, SystemNode, SystemNodeType
from ultron.core.objective_tracker import ObjectiveTracker
from ultron.core.agent_context_builder import AgentContextBuilder, CanonicalAgentContext
from ultron.core.development_session import DevelopmentSessionManager
from ultron.core.safety_evaluator import SafetyEvaluator


class TestDevelopmentSessionOrchestration(unittest.TestCase):
    def setUp(self):
        self.repo_dir = tempfile.mkdtemp(prefix="ultron_session_test_")
        self.other_repo_dir = tempfile.mkdtemp(prefix="ultron_other_test_")

        # Create baseline repository structure
        os.makedirs(os.path.join(self.repo_dir, "core"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "tests"), exist_ok=True)

        self.main_file = os.path.join(self.repo_dir, "main.py")
        with open(self.main_file, "w", encoding="utf-8") as f:
            f.write("def start():\n    return 'server ready'\n")

        self.test_file = os.path.join(self.repo_dir, "tests", "test_main.py")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("import unittest\nfrom main import start\n\nclass TestMain(unittest.TestCase):\n    def test_start(self):\n        self.assertEqual(start(), 'server ready')\n")

    def tearDown(self):
        for d in (self.repo_dir, self.other_repo_dir):
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)

    def test_complete_12_step_development_session_orchestration(self):
        """
        Executes the full 12-step development orchestration loop:
        Happy path + Failure path + State continuity.
        """
        # =========================================================================
        # Step 1: Connect to repository
        # =========================================================================
        tracker = ObjectiveTracker(self.repo_dir)
        session_mgr = DevelopmentSessionManager(self.repo_dir)
        self.assertEqual(session_mgr.get_session()["repository_root"], os.path.normcase(os.path.abspath(self.repo_dir)))

        # =========================================================================
        # Step 2: Plan objective and sequential milestones
        # =========================================================================
        obj = tracker.set_objective(
            title="Implement User Authentication",
            description="Build secure user models, password hashing, and token auth.",
            tasks=[
                {"id": "task_1", "title": "Create user model", "status": "in_progress"},
                {"id": "task_2", "title": "Implement password hashing", "status": "pending"},
                {"id": "task_3", "title": "Add JWT auth tokens", "status": "pending"}
            ],
            constraints=["Do not modify core/database.py", "Preserve existing user schemas"],
            acceptance=["All unit tests pass", "Zero unhandled exceptions"],
            affected_areas=["core/user.py", "core/auth.py"]
        )
        self.assertEqual(obj["progress_pct"], 0.0)
        self.assertEqual(len(obj["tasks"]), 3)

        # =========================================================================
        # Step 3: Start / Synchronize Development Session
        # =========================================================================
        session = session_mgr.sync_objective(obj, snapshot_id="snap_t0_baseline")
        self.assertEqual(session["current_task_id"], "task_1")
        self.assertEqual(session["current_task_title"], "Create user model")
        self.assertEqual(session["starting_snapshot_id"], "snap_t0_baseline")

        # =========================================================================
        # Step 4: Build Grounded Mission Envelope for AI Agent
        # =========================================================================
        ctx: CanonicalAgentContext = AgentContextBuilder.build(
            objective_state=obj,
            repo_path=self.repo_dir,
            snapshot_id="snap_t0_baseline",
            model_hash="model_hash_t0_1234",
            mission_intent="Implement robust token authentication",
            why_this_task_matters="User model is foundational for password hashing and authentication sessions.",
            forbidden_changes=["core/database.py"],
            next_safe_action="Implement user model in core/user.py"
        )
        self.assertEqual(ctx.active_task["id"], "task_1")
        self.assertEqual(ctx.snapshot_id, "snap_t0_baseline")
        self.assertIn("core/database.py", ctx.forbidden_changes)
        
        # Verify provider renderers
        md_env = AgentContextBuilder.render_markdown(ctx)
        self.assertIn("ULTRON MISSION ENVELOPE", md_env)
        self.assertIn("Create user model", md_env)

        claude_env = AgentContextBuilder.render_claude(ctx)
        self.assertIn("<ultron_mission_envelope", claude_env)

        cursor_env = AgentContextBuilder.render_cursor(ctx)
        self.assertIn("Cursor Mission Envelope", cursor_env)

        aider_env = AgentContextBuilder.render_aider(ctx)
        self.assertIn("Aider Mission Directive", aider_env)

        # =========================================================================
        # Step 5: Simulate AI Agent making a real code modification (Scenario A: Good change)
        # =========================================================================
        user_mod_path = os.path.join(self.repo_dir, "core", "user.py")
        with open(user_mod_path, "w", encoding="utf-8") as f:
            f.write("class User:\n    def __init__(self, username):\n        self.username = username\n    def get_name(self):\n        return self.username\n")

        user_test_path = os.path.join(self.repo_dir, "tests", "test_user.py")
        with open(user_test_path, "w", encoding="utf-8") as f:
            f.write("import unittest\nfrom core.user import User\n\nclass TestUser(unittest.TestCase):\n    def test_user(self):\n        u = User('alice')\n        self.assertEqual(u.get_name(), 'alice')\n")

        # =========================================================================
        # Step 6: Re-analyze repository state (t0 -> t1)
        # =========================================================================
        mgr_t0 = SystemModelManager()
        mgr_t0.add_node(SystemNode(id="module:main.py", type=SystemNodeType.MODULE, file_path="main.py", facts={"loc": 2}))

        mgr_t1 = SystemModelManager()
        mgr_t1.add_node(SystemNode(id="module:main.py", type=SystemNodeType.MODULE, file_path="main.py", facts={"loc": 2}))
        mgr_t1.add_node(SystemNode(id="module:core/user.py", type=SystemNodeType.MODULE, file_path="core/user.py", facts={"loc": 6}))
        mgr_t1.add_node(SystemNode(id="module:tests/test_user.py", type=SystemNodeType.MODULE, file_path="tests/test_user.py", facts={"loc": 7}))

        # =========================================================================
        # Step 7: Compute Structural Evolution Delta (SnapshotDiff)
        # =========================================================================
        evo_session = session_mgr.compute_and_record_evolution_step(
            graph_before=mgr_t0.graph,
            graph_after=mgr_t1.graph,
            snapshot_id_before="snap_t0_baseline",
            snapshot_id_after="snap_t1_user_model",
            risks_before=[{"file": "main.py", "complexity": 1.0, "coupling_score": 0.0, "level": "LOW"}],
            risks_after=[
                {"file": "main.py", "complexity": 1.0, "coupling_score": 0.0, "level": "LOW"},
                {"file": "core/user.py", "complexity": 2.0, "coupling_score": 0.0, "level": "LOW"}
            ],
            test_failures_count=0,
            forbidden_modifications=[]
        )

        delta = evo_session["evolution_delta"]
        self.assertIn("core/user.py", delta["observed"]["files_added"])
        self.assertEqual(delta["derived"]["complexity_delta"], 2.0)
        self.assertEqual(delta["can_we_continue"], "CONTINUE BUILDING")
        self.assertEqual(evo_session["safety_assessment"]["safe_to_continue"], True)

        # =========================================================================
        # Step 8: Safety & Continuation Readiness Evaluation
        # =========================================================================
        self.assertEqual(evo_session["safety_assessment"]["decision"], "CONTINUE BUILDING")
        self.assertEqual(len(evo_session["safety_assessment"]["reason_codes"]), 0)

        # =========================================================================
        # Step 9: Advance Milestone (Task 1 Complete -> Auto-promote Task 2)
        # =========================================================================
        updated_res = tracker.complete_task("task_1")
        self.assertTrue(updated_res["success"])
        updated_obj = updated_res["state"]
        self.assertEqual(updated_obj["progress_pct"], 33.3)
        self.assertEqual(updated_obj["tasks"][0]["status"], "done")
        self.assertEqual(updated_obj["tasks"][1]["status"], "in_progress")

        # Sync session after task promotion
        session_t2 = session_mgr.sync_objective(updated_obj, snapshot_id="snap_t1_user_model")
        self.assertEqual(session_t2["current_task_id"], "task_2")
        self.assertEqual(session_t2["current_task_title"], "Implement password hashing")

        # =========================================================================
        # Step 10: Generate updated Mission Envelope for Task 2
        # =========================================================================
        ctx_t2 = AgentContextBuilder.build(
            objective_state=updated_obj,
            repo_path=self.repo_dir,
            snapshot_id="snap_t1_user_model",
            model_hash="model_hash_t1_5678",
            why_this_task_matters="Password hashing secures credentials prior to generating tokens."
        )
        self.assertEqual(ctx_t2.active_task["id"], "task_2")
        self.assertEqual(len(ctx_t2.completed_tasks), 1)
        self.assertEqual(ctx_t2.completed_tasks[0]["id"], "task_1")

        # =========================================================================
        # Step 11: Failure Path (Scenario B: Bad change touches forbidden file / failing tests)
        # =========================================================================
        # Simulate agent touching forbidden file core/database.py
        db_path = os.path.join(self.repo_dir, "core", "database.py")
        with open(db_path, "w", encoding="utf-8") as f:
            f.write("# unauthorized modification\n")

        # Compute evolution delta with forbidden modification
        failed_session = session_mgr.compute_and_record_evolution_step(
            graph_before=mgr_t1.graph,
            graph_after=mgr_t1.graph,
            snapshot_id_before="snap_t1_user_model",
            snapshot_id_after="snap_t2_corrupted",
            test_failures_count=1,  # Simulated failing test
            forbidden_modifications=["core/database.py"]
        )

        self.assertEqual(failed_session["safety_assessment"]["safe_to_continue"], False)
        self.assertEqual(failed_session["safety_assessment"]["decision"], "PAUSE & REVIEW")
        self.assertIn("TESTS_FAILING", failed_session["safety_assessment"]["reason_codes"])
        self.assertIn("BOUNDARY_VIOLATION", failed_session["safety_assessment"]["reason_codes"])

        # =========================================================================
        # Step 12: State Continuity across Reloads & Repository Switching
        # =========================================================================
        # Verify exact reload persistence from disk
        fresh_mgr = DevelopmentSessionManager(self.repo_dir)
        reloaded_session = fresh_mgr.get_session()
        self.assertEqual(reloaded_session["session_id"], session["session_id"])
        self.assertEqual(reloaded_session["current_task_id"], "task_2")

        # Verify repository switching isolation
        other_mgr = DevelopmentSessionManager(self.other_repo_dir)
        other_session = other_mgr.get_session()
        self.assertNotEqual(other_session["repository_id"], session["repository_id"])
        self.assertEqual(other_session["current_task_id"], "")

        # Verify semantic timeline events
        timeline = session_mgr.get_session().get("timeline", [])
        self.assertTrue(len(timeline) >= 3)
        event_types = [e["event_type"] for e in timeline]
        self.assertIn("SESSION_STARTED", event_types)
        self.assertIn("TASK_PROMOTED", event_types)
        self.assertIn("CODE_CHANGED", event_types)
        self.assertIn("READINESS_CHECKED", event_types)


if __name__ == "__main__":
    unittest.main()
