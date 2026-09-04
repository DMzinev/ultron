"""
ultron.tests.test_real_feature_delivery
Automated tests for Phase 1.8: Real Feature Delivery and Visual Agent Control.

Covers:
1. test_browser_snapshot_before_after_same_viewport
2. test_visual_delta_detects_actual_overlap
3. test_visual_delta_detects_clipped_primary_action
4. test_visual_delta_detects_primary_cta_shift
5. test_visual_delta_ignores_intentionally_hidden_elements
6. test_browser_console_errors_block_human_pillar
7. test_browser_network_failure_propagates_to_connectivity_pillar
8. test_repair_mission_contains_actual_failure_evidence
9. test_repair_attempt_links_to_original_attempt
10. test_real_feature_iteration_a_b_c (Good agent, Bad agent recovery, Regression guard)
"""

import os
import io
import json
import shutil
import tempfile
import unittest
from typing import Dict, Any

from ultron.core.ui_reality_compiler import UIRealityCompiler
from ultron.core.issue_orchestrator import IssueOrchestrator
from ultron.core.issue_memory import IssueRecord
from ultron.core.models import build_snapshot_id
from ultron.core.development_session import DevelopmentAttempt


class TestRealFeatureDelivery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_feat_test_")
        self.ultron_dir = os.path.join(self.test_dir, ".ultron")
        os.makedirs(self.ultron_dir, exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "ultron", "interfaces", "web"), exist_ok=True)

        # Create minimal index.html fixture
        self.html_path = os.path.join(self.test_dir, "ultron", "interfaces", "web", "index.html")
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head><title>Ultron Test</title></head>
<body>
    <button id="btn-connect-repo" class="btn primary">Connect</button>
    <div id="overview-tab">
        <button id="btn-browse-repo" class="btn secondary">Browse</button>
        <button id="btn-current-work-action" class="btn primary">Start</button>
    </div>
</body>
</html>""")

        # Sample source file
        self.sample_src = os.path.join(self.test_dir, "app.py")
        with open(self.sample_src, "w", encoding="utf-8") as f:
            f.write("def compute():\n    return 42\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # 1. Viewport Consistency Invariant
    def test_browser_snapshot_before_after_same_viewport(self):
        before = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": []
        }
        after_drift = {
            "viewport": {"width": 1280, "height": 720, "device_scale_factor": 1.0},
            "elements": []
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after_drift)
        self.assertFalse(delta["passed"])
        self.assertFalse(delta["viewport_consistent"])
        self.assertTrue(any("Viewport inconsistency" in r for r in delta["reasons"]))

        # Matching viewports
        after_match = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": []
        }
        delta_ok = UIRealityCompiler.compile_browser_visual_delta(before, after_match)
        self.assertTrue(delta_ok["viewport_consistent"])

    # 2. Overlap Detection
    def test_visual_delta_detects_actual_overlap(self):
        before = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": []
        }
        # Two overlapping buttons in OVERVIEW stage
        after = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": [
                {"id": "btn-action-a", "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 100, "y": 100, "width": 120, "height": 40},
                {"id": "btn-action-b", "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 150, "y": 110, "width": 120, "height": 40}
            ]
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after)
        self.assertFalse(delta["passed"])
        self.assertGreater(len(delta["overlaps"]), 0)
        self.assertEqual(delta["overlaps"][0]["element_a"], "btn-action-a")
        self.assertEqual(delta["overlaps"][0]["element_b"], "btn-action-b")

    # 3. Clipped Primary Action Detection
    def test_visual_delta_detects_clipped_primary_action(self):
        before = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": []
        }
        # Primary CTA rendered below fold (y=920 > viewport 900)
        after = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": [
                {"id": "btn-current-work-action", "classes": ["primary"], "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 100, "y": 920, "width": 140, "height": 40}
            ]
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after)
        self.assertFalse(delta["passed"])
        self.assertGreater(len(delta["clipped_actions"]), 0)
        self.assertTrue(any("clipped" in r for r in delta["reasons"]))

    # 4. Primary CTA Shift & Competing CTAs
    def test_visual_delta_detects_primary_cta_shift(self):
        before = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "dominant_actions": {"OVERVIEW": "btn-browse-repo"},
            "elements": []
        }
        after = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "dominant_actions": {"OVERVIEW": "btn-rogue-action"},
            "action_priority_conflicts": ["Stage 'OVERVIEW' has 2 competing primary CTAs"],
            "elements": []
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after)
        self.assertFalse(delta["passed"])
        self.assertGreater(len(delta["hierarchy_violations"]), 0)

    # 5. Intentionally Hidden vs Zero-Size Visible Element
    def test_visual_delta_ignores_intentionally_hidden_elements(self):
        before = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": []
        }
        after = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": [
                # Intentionally hidden element (display: none) -> Ignored
                {"id": "modal-hidden", "visible": False, "computed_styles": {"display": "none"}, "width": 0, "height": 0, "text": "Hidden"},
                # Intentionally hidden via attribute
                {"id": "drawer-hidden", "hidden": True, "visible": True, "width": 0, "height": 0, "text": "Drawer"},
                # Broken 0px visible element with real text -> Violation
                {"id": "broken-banner", "visible": True, "computed_styles": {"display": "block"}, "width": 0, "height": 0, "text": "Important Alert"}
            ]
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after)
        self.assertFalse(delta["passed"])
        self.assertEqual(len(delta["empty_space_violations"]), 1)
        self.assertEqual(delta["empty_space_violations"][0]["id"], "broken-banner")

    # 6. Browser Console Errors Block Human Pillar
    def test_browser_console_errors_block_human_pillar(self):
        before = {"viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0}, "elements": []}
        after = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "console_errors": ["Uncaught TypeError: Cannot read properties of undefined"],
            "elements": []
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after)
        self.assertFalse(delta["passed"])
        self.assertEqual(delta["console_errors_count"], 1)

    # 7. Network Failure Handling
    def test_browser_network_failure_propagates_to_connectivity_pillar(self):
        before = {"viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0}, "elements": []}
        after = {
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "network_failures": ["POST /api/v1/work/advance net::ERR_CONNECTION_REFUSED"],
            "elements": []
        }
        delta = UIRealityCompiler.compile_browser_visual_delta(before, after)
        self.assertFalse(delta["passed"])
        self.assertEqual(delta["network_failures_count"], 1)

    # 8. Bounded Failure Packet in compile_repair_mission
    def test_repair_mission_contains_actual_failure_evidence(self):
        orch = IssueOrchestrator(self.test_dir)
        issue = IssueRecord(
            issue_id="ISSUE-REPAIR-01",
            pillar="HUMAN",
            component="ui_cockpit",
            target="ultron/interfaces/web/index.html",
            failure_class="VISUAL_COLLISION",
            symptom="Button overlap detected",
            reproduction="Inspect UI Reality Report",
            reproduction_signature="OVERLAP_btn-action-a_btn-action-b"
        )
        orch.issue_memory.record_issue(issue)
        orch.select_issue("ISSUE-REPAIR-01")
        orch.compile_mission()

        # Simulate failure
        orch.work_queue.transition_to("IMPLEMENTING")
        orch.work_queue.transition_to("OBSERVING")
        orch.work_queue.transition_to("VERIFYING")
        orch.work_queue.transition_to("REPAIR_REQUIRED", context={"blocking_reasons": ["Visual overlap detected"]})

        failure_packet = {
            "original_issue": "ISSUE-REPAIR-01",
            "attempt_id": orch.active_attempt.attempt_id,
            "snapshot_id": "snap-1234",
            "failed_pillar": "HUMAN",
            "failure_class": "VISUAL_COLLISION",
            "actual_observation": "btn-action-a overlaps btn-action-b",
            "affected_files": ["ultron/interfaces/web/index.html"],
            "visual_evidence_ref": ".ultron/evidence/ATT-ISSUE-REPAIR-01-1",
            "blocking_reasons": ["Visual overlap detected between btn-action-a and btn-action-b"]
        }

        repair_mission = orch.compile_repair_mission("ISSUE-REPAIR-01", failure_packet)
        self.assertEqual(orch.work_queue.get_state().status, "MISSION_READY")
        self.assertEqual(repair_mission["attempt_number"], 2)
        self.assertIn("Visual overlap detected", repair_mission["instructions"])
        self.assertEqual(repair_mission["failure_packet"]["failed_pillar"], "HUMAN")

    # 9. Parent Attempt Linking
    def test_repair_attempt_links_to_original_attempt(self):
        orch = IssueOrchestrator(self.test_dir)
        issue = IssueRecord(
            issue_id="ISSUE-LINK-01",
            pillar="FUNCTIONAL",
            component="ast",
            target="app.py",
            failure_class="COMPLEXITY_HOTSPOT",
            symptom="Refactor function",
            reproduction="run tests"
        )
        orch.issue_memory.record_issue(issue)
        orch.select_issue("ISSUE-LINK-01")
        orch.compile_mission()

        orig_attempt_id = orch.active_attempt.attempt_id
        orch.work_queue.transition_to("IMPLEMENTING")
        orch.work_queue.transition_to("OBSERVING")
        orch.work_queue.transition_to("VERIFYING")
        orch.work_queue.transition_to("REPAIR_REQUIRED", context={"blocking_reasons": ["Test failed"]})

        repair = orch.compile_repair_mission("ISSUE-LINK-01", {"blocking_reasons": ["Test failed"]})
        self.assertEqual(orch.active_attempt.parent_attempt_id, orig_attempt_id)
        self.assertEqual(orch.active_attempt.attempt_number, 2)
        self.assertTrue(orch.active_attempt.attempt_id.endswith("-2"))

    # 10. Complete Multi-Iteration Lifecycle: Iteration A -> B -> C
    def test_real_feature_iteration_a_b_c(self):
        orch = IssueOrchestrator(self.test_dir)

        # --- ITERATION A: Good Agent (Clean Pass) ---
        iss_a = IssueRecord(
            issue_id="FEAT-01",
            pillar="FUNCTIONAL",
            component="core",
            target="app.py",
            failure_class="ENHANCEMENT",
            symptom="Add helper function",
            reproduction="test app.py",
            reproduction_signature="SIG_FEAT_01"
        )
        orch.issue_memory.record_issue(iss_a)
        orch.select_issue("FEAT-01")
        orch.compile_mission()

        # Agent executes clean change
        orch.execute_attempt(modified_files=["app.py"])
        snap_a = build_snapshot_id("content_hash_rev1")
        test_res_a = {"passed_count": 5, "failed_count": 0, "passed": True}
        orch.observe_state(snapshot_id=snap_a, test_results=test_res_a)

        # Verification passes
        is_ver_a, reasons_a = orch.verify_attempt()
        self.assertTrue(is_ver_a, f"Iteration A failed verification: {reasons_a}")
        orch.guard_regression_and_advance()
        self.assertEqual(orch.work_queue.get_state().status, "CHECKPOINT_READY")
        chk_a = orch.checkpoint_progression("Iteration A clean delivery")
        self.assertTrue(chk_a.startswith("CHK-"))
        self.assertEqual(orch.issue_memory.get_issue("FEAT-01").status, "REGRESSION_GUARD")

        # --- ITERATION B: Bad Agent (Visual Defect -> Caught -> Repaired -> Checkpointed) ---
        iss_b = IssueRecord(
            issue_id="FEAT-02",
            pillar="HUMAN",
            component="web",
            target="ultron/interfaces/web/index.html",
            failure_class="VISUAL_REGRESSION",
            symptom="Overlapping action buttons",
            reproduction="Audit UI Reality",
            reproduction_signature="SIG_FEAT_02"
        )
        # Transition to DISCOVERING for Iteration B
        orch.discover_issues()
        orch.issue_memory.record_issue(iss_b)
        orch.select_issue("FEAT-02")
        orch.compile_mission()

        # Bad agent execution (creates visual collision)
        orch.execute_attempt(modified_files=["ultron/interfaces/web/index.html"])
        snap_b1 = build_snapshot_id("content_hash_b1")
        bad_visual = {
            "snapshot_id": snap_b1,
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": [
                {"id": "btn-1", "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 50, "y": 50, "width": 100, "height": 40},
                {"id": "btn-2", "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 80, "y": 60, "width": 100, "height": 40}
            ]
        }
        orch.observe_state(snapshot_id=snap_b1, test_results={"passed_count": 5, "failed_count": 0, "passed": True}, visual_snapshot=bad_visual)

        # Verification must catch the defect
        is_ver_b1, reasons_b1 = orch.verify_attempt()
        self.assertFalse(is_ver_b1, "Bad agent should have failed verification!")
        self.assertTrue(any("Human Reality Pillar Failed" in r for r in reasons_b1))

        # Transition to REPAIR_REQUIRED
        orch.guard_regression_and_advance()
        self.assertEqual(orch.work_queue.get_state().status, "REPAIR_REQUIRED")

        # Compile repair mission with diagnostics
        repair_packet = {
            "failed_pillar": "HUMAN",
            "blocking_reasons": reasons_b1,
            "affected_files": ["ultron/interfaces/web/index.html"]
        }
        orch.compile_repair_mission("FEAT-02", repair_packet)
        self.assertEqual(orch.work_queue.get_state().status, "MISSION_READY")
        self.assertEqual(orch.active_attempt.attempt_number, 2)

        # Agent repairs the defect (layout resolved)
        orch.execute_attempt(modified_files=["ultron/interfaces/web/index.html"])
        snap_b2 = build_snapshot_id("content_hash_b2")
        good_visual = {
            "snapshot_id": snap_b2,
            "viewport": {"width": 1440, "height": 900, "device_scale_factor": 1.0},
            "elements": [
                {"id": "btn-1", "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 50, "y": 50, "width": 100, "height": 40},
                {"id": "btn-2", "stage": "OVERVIEW", "is_interactive": True, "visible": True, "x": 200, "y": 50, "width": 100, "height": 40}
            ]
        }
        orch.observe_state(snapshot_id=snap_b2, test_results={"passed_count": 5, "failed_count": 0, "passed": True}, visual_snapshot=good_visual)

        # Re-verification passes cleanly
        is_ver_b2, reasons_b2 = orch.verify_attempt()
        self.assertTrue(is_ver_b2, f"Repaired attempt should pass: {reasons_b2}")
        orch.guard_regression_and_advance()
        self.assertEqual(orch.work_queue.get_state().status, "CHECKPOINT_READY")
        chk_b = orch.checkpoint_progression("Iteration B repaired delivery")
        self.assertTrue(chk_b.startswith("CHK-"))

        # --- ITERATION C: Regression Defense (Re-inject FEAT-01 defect) ---
        iss_c = IssueRecord(
            issue_id="FEAT-03",
            pillar="FUNCTIONAL",
            component="core",
            target="app.py",
            failure_class="ENHANCEMENT",
            symptom="New change",
            reproduction="test app.py"
        )
        # Transition to DISCOVERING for Iteration C
        orch.discover_issues()
        orch.issue_memory.record_issue(iss_c)
        orch.select_issue("FEAT-03")
        orch.compile_mission()

        # Injected failure matching FEAT-01 signature
        orch.execute_attempt(modified_files=["app.py"])
        snap_c = build_snapshot_id("content_hash_c")
        test_res_c = {
            "passed_count": 4,
            "failed_count": 1,
            "passed": False,
            "failures": "AssertionError: SIG_FEAT_01 regression detected in app.py"
        }
        orch.observe_state(snapshot_id=snap_c, test_results=test_res_c)

        is_ver_c, reasons_c = orch.verify_attempt()
        self.assertFalse(is_ver_c)
        self.assertTrue(any("Regression Detected" in r for r in reasons_c))

        # FEAT-01 must have been automatically reopened in IssueMemory
        reopened_issue = orch.issue_memory.get_issue("FEAT-01")
        self.assertEqual(reopened_issue.status, "REOPENED")

    # 11. Server Endpoint Dispatch Integration
    def test_server_work_visual_delta_endpoint(self):
        from ultron.interfaces.server import UltronAPIHandler
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/work/visual-delta"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.test_dir

        handler.handle_work_visual_delta()
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("visual_delta", data)


if __name__ == "__main__":
    unittest.main()
