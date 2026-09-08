"""
Ultron Phase 1.9 — Real Product Improvement Tests

Tests the Seamless Mission Handoff & Multi-Provider Agent Context Synchronization
feature, real Edge headless browser PNG capture, human judgment enforcement,
and provider semantic equivalence.
"""
import os
import sys
import json
import time
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


class TestAgentContextBuilderIntentAndTargetFile(unittest.TestCase):
    """Tests AgentContextBuilder.build() accepts intent and target_file parameters."""

    def test_build_with_intent_and_target_file(self):
        from ultron.core.agent_context_builder import AgentContextBuilder
        ctx = AgentContextBuilder.build(
            objective_state={"title": "Test Objective", "tasks": []},
            repo_path=ROOT,
            intent="Fix the server crash on empty POST body",
            target_file="ultron/interfaces/server.py"
        )
        self.assertIn("Fix the server crash", ctx.mission_intent)
        self.assertIn("ultron/interfaces/server.py", ctx.affected_components)

    def test_build_with_intent_overrides_objective_description(self):
        from ultron.core.agent_context_builder import AgentContextBuilder
        ctx = AgentContextBuilder.build(
            objective_state={"title": "Generic Objective", "description": "Do something generic", "tasks": []},
            repo_path=ROOT,
            intent="Specific fix: handle None in provider pills"
        )
        self.assertEqual(ctx.mission_intent, "Specific fix: handle None in provider pills")

    def test_build_with_none_objective_state(self):
        """Ensures build() does not crash when objective_state is None."""
        from ultron.core.agent_context_builder import AgentContextBuilder
        ctx = AgentContextBuilder.build(
            objective_state=None,
            repo_path=ROOT,
            intent="Test intent",
            target_file="ultron/core/pipeline/orchestrator.py"
        )
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.mission_intent, "Test intent")


class TestProviderSwitchPreservesSemanticMissionIdentity(unittest.TestCase):
    """
    For every provider (Claude, Cursor, Antigravity, Aider, Markdown),
    verifies that target_files, intent, issue_id, acceptance, and boundaries
    remain semantically identical while allowing format differences.
    """

    def test_provider_switch_preserves_semantic_mission_identity(self):
        from ultron.core.agent_context_builder import AgentContextBuilder

        intent = "Fix race condition in repository loading"
        target = "ultron/interfaces/server.py"
        obj = {
            "title": "Repository Race Fix",
            "tasks": [{"title": "Fix race", "status": "active", "file": target}],
            "affected_areas": [target],
            "acceptance": ["Server handles concurrent requests without crash"],
            "constraints": ["Do not modify test_runner_service.py"]
        }

        ctx = AgentContextBuilder.build(
            objective_state=obj,
            repo_path=ROOT,
            intent=intent,
            target_file=target
        )

        renders = {
            "markdown": AgentContextBuilder.render_markdown(ctx),
            "claude": AgentContextBuilder.render_claude(ctx),
            "codex": AgentContextBuilder.render_codex(ctx),
            "antigravity": AgentContextBuilder.render_antigravity(ctx),
            "aider": AgentContextBuilder.render_aider(ctx),
        }

        # Semantic invariant: every provider render must contain the same mission content
        for name, rendered in renders.items():
            self.assertIn(target, rendered,
                          f"Provider '{name}' lost target_file '{target}'")
            self.assertIn(intent, rendered,
                          f"Provider '{name}' lost intent '{intent}'")

        # Format must differ (at least some providers use different syntax)
        unique_renders = set(renders.values())
        self.assertGreater(len(unique_renders), 1,
                           "All providers rendered identical output — format differentiation failed")


class TestUIRealityReportStatusMessage(unittest.TestCase):
    """Tests UIRealityReport epistemic terminology invariant."""

    def test_status_message_default(self):
        from ultron.core.ui_reality_compiler import UIRealityReport
        report = UIRealityReport()
        self.assertEqual(report.status_message,
                         "No known automated visual contract violation was detected")

    def test_summary_passed_contains_status_message(self):
        from ultron.core.ui_reality_compiler import UIRealityReport
        report = UIRealityReport(passed=True)
        summary = report.summary()
        self.assertIn("No known automated visual contract violation was detected", summary)
        self.assertNotIn("The UI is good", summary)

    def test_summary_failed_does_not_say_good(self):
        from ultron.core.ui_reality_compiler import UIRealityReport
        report = UIRealityReport(passed=False)
        summary = report.summary()
        self.assertIn("FAIL", summary)
        self.assertNotIn("The UI is good", summary)

    def test_browser_reality_field(self):
        from ultron.core.ui_reality_compiler import UIRealityReport
        report = UIRealityReport(browser_reality="FULL")
        self.assertEqual(report.browser_reality, "FULL")
        report_degraded = UIRealityReport(browser_reality="DEGRADED")
        self.assertEqual(report_degraded.browser_reality, "DEGRADED")


class TestBrowserRealityCapture(unittest.TestCase):
    """Tests real Edge headless PNG capture with phase awareness."""

    def test_capture_before_phase(self):
        from ultron.core.ui_reality_compiler import UIRealityCompiler
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal HTML for capture
            web_dir = os.path.join(tmpdir, "ultron", "interfaces", "web")
            os.makedirs(web_dir, exist_ok=True)
            with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write("<html><body><h1>Test Before</h1></body></html>")

            result = UIRealityCompiler.capture_browser_reality(
                repo_root=tmpdir,
                attempt_id="ATT-TEST-BEFORE",
                phase="before"
            )
            self.assertEqual(result["phase"], "before")
            self.assertIn(result["browser_reality"], ("FULL", "DEGRADED"))

            evidence_dir = os.path.join(tmpdir, ".ultron", "evidence", "ATT-TEST-BEFORE")
            self.assertTrue(os.path.exists(evidence_dir))

            # JSON metadata must exist
            json_path = os.path.join(evidence_dir, "before.json")
            self.assertTrue(os.path.exists(json_path))
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["phase"], "before")
            self.assertIn("environment_invariants", meta)
            self.assertEqual(meta["environment_invariants"]["viewport"]["width"], 1440)

            # If Edge is available, PNG must exist
            if result["browser_reality"] == "FULL":
                png_path = os.path.join(evidence_dir, "before.png")
                self.assertTrue(os.path.exists(png_path))
                self.assertGreater(os.path.getsize(png_path), 0)

    def test_capture_after_phase(self):
        from ultron.core.ui_reality_compiler import UIRealityCompiler
        with tempfile.TemporaryDirectory() as tmpdir:
            web_dir = os.path.join(tmpdir, "ultron", "interfaces", "web")
            os.makedirs(web_dir, exist_ok=True)
            with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write("<html><body><h1>Test After</h1></body></html>")

            result = UIRealityCompiler.capture_browser_reality(
                repo_root=tmpdir,
                attempt_id="ATT-TEST-AFTER",
                phase="after"
            )
            self.assertEqual(result["phase"], "after")
            json_path = os.path.join(tmpdir, ".ultron", "evidence", "ATT-TEST-AFTER", "after.json")
            self.assertTrue(os.path.exists(json_path))

    def test_environment_invariants_match_between_phases(self):
        """Before and after captures must share identical environment invariants."""
        from ultron.core.ui_reality_compiler import UIRealityCompiler
        with tempfile.TemporaryDirectory() as tmpdir:
            web_dir = os.path.join(tmpdir, "ultron", "interfaces", "web")
            os.makedirs(web_dir, exist_ok=True)
            with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write("<html><body><h1>Invariant Test</h1></body></html>")

            before = UIRealityCompiler.capture_browser_reality(tmpdir, "ATT-INV", phase="before")
            after = UIRealityCompiler.capture_browser_reality(tmpdir, "ATT-INV", phase="after")

            with open(os.path.join(tmpdir, ".ultron", "evidence", "ATT-INV", "before.json"), "r", encoding="utf-8") as f:
                before_json = json.load(f)
            with open(os.path.join(tmpdir, ".ultron", "evidence", "ATT-INV", "after.json"), "r", encoding="utf-8") as f:
                after_json = json.load(f)

            # Environment invariants must be identical
            self.assertEqual(
                before_json["environment_invariants"]["viewport"],
                after_json["environment_invariants"]["viewport"]
            )
            self.assertEqual(
                before_json["environment_invariants"]["device_scale_factor"],
                after_json["environment_invariants"]["device_scale_factor"]
            )


class TestHumanJudgmentEnforcement(unittest.TestCase):
    """Tests DevelopmentAttempt human judgment gating and IssueOrchestrator recording."""

    def test_development_attempt_human_judgment_field(self):
        from ultron.core.development_session import DevelopmentAttempt
        attempt = DevelopmentAttempt(
            attempt_id="ATT-J-01",
            issue_id="BUG-J-01",
            mission_id="MSN-J-01",
            attempt_number=1
        )
        self.assertIsNone(attempt.human_judgment)

    def test_worse_judgment_blocks_is_verified(self):
        from ultron.core.development_session import DevelopmentAttempt
        attempt = DevelopmentAttempt(
            attempt_id="ATT-J-02",
            issue_id="BUG-J-02",
            mission_id="MSN-J-02",
            attempt_number=1,
            snapshot_after="snap_123",
            tests_after={"passed_count": 5, "failed_count": 0, "passed": True},
            three_pillar_results={"FUNCTIONAL": True, "CONNECTIVITY": True, "HUMAN": True},
            human_judgment={"rating": "WORSE", "rationale": "UI is broken", "evaluated_at": "2026-01-01T00:00:00Z"}
        )
        self.assertFalse(attempt.is_verified())

    def test_better_judgment_does_not_block(self):
        from ultron.core.development_session import DevelopmentAttempt
        attempt = DevelopmentAttempt(
            attempt_id="ATT-J-03",
            issue_id="BUG-J-03",
            mission_id="MSN-J-03",
            attempt_number=1,
            snapshot_after="snap_456",
            tests_after={"passed_count": 5, "failed_count": 0, "passed": True},
            three_pillar_results={"FUNCTIONAL": True, "CONNECTIVITY": True, "HUMAN": True},
            human_judgment={"rating": "BETTER", "rationale": "Much smoother workflow", "evaluated_at": "2026-01-01T00:00:00Z"}
        )
        self.assertTrue(attempt.is_verified())

    def test_orchestrator_record_human_judgment_better(self):
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.development_session import DevelopmentAttempt
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IssueOrchestrator(repo_root=tmpdir)
            orch.active_attempt = DevelopmentAttempt(
                attempt_id="ATT-RHJ-01",
                issue_id="BUG-RHJ-01",
                mission_id="MSN-RHJ-01",
                attempt_number=1
            )
            result = orch.record_human_judgment("BETTER", "Handoff works perfectly")
            self.assertEqual(result["rating"], "BETTER")
            self.assertEqual(orch.active_attempt.outcome, "SUCCESS")
            self.assertIsNotNone(orch.active_attempt.human_judgment)

    def test_orchestrator_record_human_judgment_worse(self):
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.development_session import DevelopmentAttempt
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IssueOrchestrator(repo_root=tmpdir)
            orch.active_attempt = DevelopmentAttempt(
                attempt_id="ATT-RHJ-02",
                issue_id="BUG-RHJ-02",
                mission_id="MSN-RHJ-02",
                attempt_number=1
            )
            result = orch.record_human_judgment("WORSE", "Intent is lost on provider switch")
            self.assertEqual(result["rating"], "WORSE")
            self.assertEqual(orch.active_attempt.outcome, "FAILURE")

    def test_orchestrator_record_human_judgment_no_difference(self):
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.development_session import DevelopmentAttempt
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IssueOrchestrator(repo_root=tmpdir)
            orch.active_attempt = DevelopmentAttempt(
                attempt_id="ATT-RHJ-03",
                issue_id="BUG-RHJ-03",
                mission_id="MSN-RHJ-03",
                attempt_number=1
            )
            result = orch.record_human_judgment("NO_DIFFERENCE", "Same as before")
            self.assertEqual(result["rating"], "NO_DIFFERENCE")
            self.assertEqual(orch.active_attempt.outcome, "PRODUCT_REVIEW_REQUIRED")


class TestHTMLContainsPushButtonAndJudgment(unittest.TestCase):
    """Verifies index.html contains the required UI elements."""

    def test_push_agent_button_exists(self):
        html_path = os.path.join(ROOT, "ultron", "interfaces", "web", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("studio-compile-btn", html)
        self.assertIn("Compile Agent Mission Package", html)

    def test_human_judgment_card_exists(self):
        html_path = os.path.join(ROOT, "ultron", "interfaces", "web", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("auditor-shield", html)
        self.assertIn("auditor-run-btn", html)
        self.assertIn("auditor-verdict-title", html)

    def test_no_infinite_spinner_on_work_tab(self):
        html_path = os.path.join(ROOT, "ultron", "interfaces", "web", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertNotIn("Loading Objective Progression Plan...", html)
class TestRealProductMultiIterationLifecycle(unittest.TestCase):
    """
    Tests the complete 3-iteration lifecycle:
    - Iteration A: Valid product improvement (Clean path -> Verified -> Checkpoint -> Guard)
    - Iteration B: Real defect (intent drop) -> Failure detected -> Repair mission -> Fixed
    - Iteration C: Historical regression defense (IssueMemory intercepts regression)
    """

    def test_iteration_a_valid_product_improvement(self):
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.issue_memory import IssueRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal structure
            web_dir = os.path.join(tmpdir, "ultron", "interfaces", "web")
            os.makedirs(web_dir, exist_ok=True)
            with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write("<html><body><button id='btn-current-work-push-agent'>Send</button></body></html>")

            orch = IssueOrchestrator(repo_root=tmpdir)
            issue = IssueRecord(
                issue_id="ISSUE-HANDOFF-01",
                pillar="HUMAN",
                component="agent_context",
                target="ultron/interfaces/web/index.html",
                failure_class="DISCONNECTED_HANDOFF",
                symptom="Missing mission handoff from Current Work to Agent Context",
                reproduction="CURRENT_WORK_PUSH_AGENT_DISCONNECTED",
                reproduction_signature="CURRENT_WORK_PUSH_AGENT_DISCONNECTED"
            )
            orch.issue_memory.record_issue(issue)
            orch.select_issue("ISSUE-HANDOFF-01")
            orch.compile_mission()
            orch.execute_attempt()

            # Record before & after browser capture
            orch.active_attempt.snapshot_after = "snap_feat_01"
            orch.active_attempt.changed_files = ["ultron/interfaces/web/index.html"]
            orch.active_attempt.tests_after = {
                "passed_count": 10, "failed_count": 0, "passed": True, "snapshot_id": "snap_feat_01"
            }
            orch.active_attempt.visual_state_after = {
                "snapshot_id": "snap_feat_01",
                "action_priority_conflicts": [],
                "runtime_health": {"status": "HEALTHY"}
            }

            # Advance to observing and verifying
            orch.work_queue.transition_to("OBSERVING")
            orch.work_queue.transition_to("VERIFYING")

            # Human judgment: BETTER
            orch.record_human_judgment("BETTER", "Mission handoff works seamlessly")
            self.assertEqual(orch.active_attempt.outcome, "SUCCESS")

            # Verify and Advance
            is_verified, reasons = orch.verify_attempt()
            self.assertTrue(is_verified, f"Attempt should be verified but failed: {reasons}")

            # Guard regression and checkpoint
            state = orch.guard_regression_and_advance()
            self.assertEqual(state.status, "CHECKPOINT_READY")
            chk_id = orch.checkpoint_progression("Seamless Mission Handoff & Provider Sync")
            self.assertTrue(chk_id.startswith("CHK-"))

            # Invariant: Issue must now be guarded in IssueMemory
            guarded = orch.issue_memory.get_issue("ISSUE-HANDOFF-01")
            self.assertIsNotNone(guarded)
            self.assertEqual(guarded.status, "REGRESSION_GUARD")

    def test_iteration_b_intent_loss_defect_and_diagnostic_repair(self):
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.issue_memory import IssueRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IssueOrchestrator(repo_root=tmpdir)
            issue = IssueRecord(
                issue_id="ISSUE-PROVIDER-SYNC-01",
                pillar="HUMAN",
                component="server",
                target="ultron/interfaces/server.py",
                failure_class="INTENT_LOSS",
                symptom="Provider switch clears user intent",
                reproduction="PROVIDER_SWITCH_DROPS_INTENT"
            )
            orch.issue_memory.record_issue(issue)
            orch.select_issue("ISSUE-PROVIDER-SYNC-01")
            orch.compile_mission()
            orch.execute_attempt()

            # Simulate defective execution: Intent is lost
            orch.active_attempt.snapshot_after = "snap_broken"
            orch.active_attempt.tests_after = {
                "passed_count": 0, "failed_count": 1, "passed": False,
                "failures": "AssertionError: expected_intent='Investigate race' != actual_intent=''"
            }

            orch.work_queue.transition_to("OBSERVING")
            orch.work_queue.transition_to("VERIFYING")

            # Human rates WORSE (automatically transitions state from VERIFYING to REPAIR_REQUIRED)
            orch.record_human_judgment("WORSE", "Intent was dropped on provider switch")
            self.assertEqual(orch.active_attempt.outcome, "FAILURE")
            self.assertEqual(orch.work_queue.get_state().status, "REPAIR_REQUIRED")

            # Diagnostic Repair Mission compilation
            repair_mission = orch.compile_repair_mission(
                issue_id="ISSUE-PROVIDER-SYNC-01",
                failure_packet={
                    "blocking_reasons": ["Intent dropped on provider switch"],
                    "observed": {
                        "provider": "Antigravity",
                        "target_file": "ultron/interfaces/server.py",
                        "expected_intent": "Investigate race",
                        "actual_intent": ""
                    }
                }
            )
            self.assertIsNotNone(repair_mission)
            self.assertEqual(orch.active_attempt.attempt_number, 2)

            # Repair applied: tests now pass, human rates BETTER
            orch.active_attempt.snapshot_after = "snap_repaired"
            orch.active_attempt.tests_after = {
                "passed_count": 10, "failed_count": 0, "passed": True, "snapshot_id": "snap_repaired"
            }
            orch.active_attempt.visual_state_after = {
                "snapshot_id": "snap_repaired",
                "action_priority_conflicts": [],
                "runtime_health": {"status": "HEALTHY"}
            }
            orch.record_human_judgment("BETTER", "Intent is preserved across all providers")
            is_verified, _ = orch.verify_attempt()
            self.assertTrue(is_verified)

    def test_iteration_c_historical_regression_defense(self):
        from ultron.core.issue_orchestrator import IssueOrchestrator
        from ultron.core.issue_memory import IssueRecord
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IssueOrchestrator(repo_root=tmpdir)
            # Existing regression guard
            guard = IssueRecord(
                issue_id="GUARD-INTENT-01",
                pillar="HUMAN",
                component="server",
                target="ultron/interfaces/server.py",
                failure_class="INTENT_LOSS",
                symptom="Provider switch clears user intent",
                reproduction="PROVIDER_SWITCH_DROPS_INTENT",
                reproduction_signature="PROVIDER_SWITCH_DROPS_INTENT",
                status="REGRESSION_GUARD"
            )
            orch.issue_memory.record_issue(guard)

            # New attempt that accidentally re-introduces the bug
            orch.select_issue("GUARD-INTENT-01")
            orch.compile_mission()
            orch.execute_attempt()
            orch.active_attempt.snapshot_after = "snap_regress"
            orch.active_attempt.tests_after = {
                "passed_count": 5,
                "failed_count": 1,
                "passed": False,
                "failures": "Error: PROVIDER_SWITCH_DROPS_INTENT detected in server response"
            }

            # Verification should detect historical regression
            is_verified, reasons = orch.verify_attempt()
            self.assertFalse(is_verified)
            self.assertEqual(orch.active_attempt.outcome, "REGRESSION_DETECTED")
            reopened = orch.issue_memory.get_issue("GUARD-INTENT-01")
            self.assertEqual(reopened.status, "REOPENED")


if __name__ == "__main__":
    unittest.main()
