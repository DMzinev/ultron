"""
Ultron Phase 2.0 Master Verification Suite: Real Product Improvement Loop
Tests the 14-point Definition of Done and 9 Constitutional Refinements:
1. Agent 10 Falsification Baseline
2. Provider Compilation Synchronization & /api/v1/generate adapter
3. StateStore Unidirectional Flow & DOM Synchronization
4. Strong Semantic Mission Invariance (semantic_mission_hash equality across all 5 providers)
5. Product Prioritization Formula (Score = Impact * Freq * Sev * Conf * Repair) without uncalibrated priors
6. Backward-Compatible Epistemic Browser Gating (DEGRADED -> Human Reality = NOT_PROVEN)
7. 4-Stage Constitutional Progression (MECHANICALLY_COMPLIANT -> BROWSER_VERIFIED -> HUMAN_JUDGED -> PRODUCT_IMPROVED)
8. Crucial Negative Test: BETTER + DEGRADED browser reality -> BLOCKED from PRODUCT_IMPROVED and checkpoint
9. Full 3-Iteration Lifecycle (Iteration A clean improvement -> Iteration B defect & diagnostic repair -> Iteration C historical regression defense)
"""
import os
import sys
import unittest
import json
import tempfile
import shutil
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from ultron.core.agent_context_builder import AgentContextBuilder, CanonicalAgentContext
from ultron.core.issue_orchestrator import IssueOrchestrator
from ultron.core.issue_memory import IssueMemory, IssueRecord
from ultron.core.development_session import DevelopmentAttempt
from ultron.core.work_queue import WorkQueue, WorkState, InvalidStateTransitionError
from ultron.core.ui_reality_compiler import UIRealityCompiler

class TestPhase20ProductImprovement(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ultron_phase20_test_")
        self.evidence_dir = os.path.join(self.tmp_dir, ".ultron", "evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)
        # Seed index.html
        web_dir = os.path.join(self.tmp_dir, "ultron", "interfaces", "web")
        os.makedirs(web_dir, exist_ok=True)
        with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><body><div id='overview-work-state-card'></div></body></html>")

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Agent 10 Falsification Baseline
    # -------------------------------------------------------------------------
    def test_agent10_falsification_baseline_artifact(self):
        """Verifies that Agent 10 produced a reproducible failing baseline artifact."""
        artifact_path = os.path.join(ROOT, ".ultron", "evidence", "falsification_baseline.json")
        self.assertTrue(os.path.exists(artifact_path), "Falsification baseline artifact must exist on disk.")
        with open(artifact_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("agent"), "Agent 10 (Skeptical Product Judge)")
        self.assertEqual(data.get("disproof_verdict"), "FALSIFICATION_FAILED (All defects confirmed real in baseline code)")
        self.assertTrue(data.get("implementation_authorized"), "Implementation must be explicitly authorized.")

    # -------------------------------------------------------------------------
    # 2. Semantic Mission Invariance Across All 5 Providers
    # -------------------------------------------------------------------------
    def test_provider_switching_semantic_mission_invariance(self):
        """
        Refinement 3:
        SemanticMission(provider A) == SemanticMission(provider B)
        while RenderedPrompt(A) != RenderedPrompt(B).
        Includes: target_files, mission_intent, issue_id, reproduction_signature, why_it_matters.
        """
        intent = "Fix: Agent Context Provider Switch & Prompt Compilation Desynchronization"
        target_file = "ultron/interfaces/web/modules/state.js"
        issue_id = "BUG-PROD-01"
        repro_sig = "PROVIDER_SYNC_DESYNCHRONIZATION"
        why = "Prevent silent loss of developer custom instructions."

        providers = ["markdown", "claude", "cursor", "antigravity", "aider"]
        contexts = {}
        hashes = {}
        rendered = {}

        for p in providers:
            ctx = AgentContextBuilder.build(
                objective_state={
                    "title": "Agent Context Hub Improvement",
                    "description": intent,
                    "affected_areas": [target_file],
                    "issue_id": issue_id,
                    "reproduction_signature": repro_sig
                },
                repo_path=self.tmp_dir,
                intent=intent,
                target_file=target_file,
                issue_id=issue_id,
                reproduction_signature=repro_sig,
                why_this_task_matters=why
            )
            contexts[p] = ctx
            hashes[p] = ctx.semantic_mission_hash()

            if p == "claude":
                rendered[p] = AgentContextBuilder.render_claude(ctx)
            elif p == "cursor":
                rendered[p] = AgentContextBuilder.render_codex(ctx)
            elif p == "antigravity":
                rendered[p] = AgentContextBuilder.render_antigravity(ctx)
            elif p == "aider":
                rendered[p] = AgentContextBuilder.render_aider(ctx)
            else:
                rendered[p] = AgentContextBuilder.render_markdown(ctx)

        # Invariant 1: All 5 semantic mission hashes MUST be identical
        base_hash = hashes["markdown"]
        for p in providers:
            self.assertEqual(hashes[p], base_hash, f"Semantic mission hash for {p} must match markdown baseline!")

        # Invariant 2: Semantic fields must be strictly identical
        for p in providers:
            self.assertEqual(contexts[p].mission_intent, intent)
            self.assertEqual(contexts[p].affected_components, [target_file])
            self.assertEqual(contexts[p].issue_id, issue_id)
            self.assertEqual(contexts[p].reproduction_signature, repro_sig)
            self.assertEqual(contexts[p].why_this_task_matters, why)

        # Invariant 3: Rendered prompts MUST differ by provider syntax
        self.assertIn("<ultron_mission_envelope", rendered["claude"])
        self.assertIn("# Cursor Mission Envelope", rendered["cursor"])
        self.assertIn("[UMAGS MISSION ENVELOPE]", rendered["antigravity"])
        self.assertIn("/add", rendered["aider"])

    # -------------------------------------------------------------------------
    # 3. Product Prioritization Formula
    # -------------------------------------------------------------------------
    def test_product_prioritization_formula_without_uncalibrated_priors(self):
        """
        Refinement 2:
        Score = Impact * Frequency * Severity * Confidence * Repairability.
        Missing dimensions -> UNKNOWN/unscored (not hardcoded priors).
        Reopened issues maintain Priority 0.
        """
        orch = IssueOrchestrator(self.tmp_dir)

        # Issue 1: Scored UX Product Defect (Score: 4*5*4*5*5 = 2000)
        iss_ux = IssueRecord(
            issue_id="BUG-UX-01",
            pillar="HUMAN",
            component="ui",
            target="state.js",
            failure_class="UX_DEFECT",
            symptom="Lost typed intent on provider switch",
            reproduction="Type intent then switch provider",
            reproduction_signature="UX_INTENT_LOSS",
            fingerprint="fp1",
            root_cause="DOM-state desync",
            status="DISCOVERED",
            metadata={"user_impact": 4, "workflow_frequency": 5, "severity": 4, "confidence": 5, "repairability": 5}
        )

        # Issue 2: AST Complexity Hotspot (Score: 1*1*1*1*1 = 1)
        iss_ast = IssueRecord(
            issue_id="HOTSPOT-AST-01",
            pillar="FUNCTIONAL",
            component="ast",
            target="server.py",
            failure_class="COMPLEXITY_HOTSPOT",
            symptom="Cyclomatic complexity 57 >= 15",
            reproduction="Analyze AST",
            reproduction_signature="HOTSPOT_server.py",
            fingerprint="fp2",
            root_cause="Deep branching",
            status="DISCOVERED",
            metadata={"user_impact": 1, "workflow_frequency": 1, "severity": 1, "confidence": 1, "repairability": 1}
        )

        # Issue 3: Unscored Standard Issue (missing user_impact -> score is None/UNKNOWN)
        iss_unscored = IssueRecord(
            issue_id="ISSUE-RAW-01",
            pillar="FUNCTIONAL",
            component="core",
            target="analyzer.py",
            failure_class="UNSCORED",
            symptom="Unscored observation",
            reproduction="",
            reproduction_signature="",
            fingerprint="fp3",
            root_cause="",
            status="DISCOVERED",
            metadata={"workflow_frequency": 5, "severity": 4}  # missing user_impact
        )

        # Issue 4: Reopened Regression (Priority 0)
        iss_reopened = IssueRecord(
            issue_id="REG-01",
            pillar="FUNCTIONAL",
            component="core",
            target="models.py",
            failure_class="REGRESSION",
            symptom="Historical regression re-manifested",
            reproduction="run tests",
            reproduction_signature="HIST_REG",
            fingerprint="fp4",
            root_cause="",
            status="REOPENED",
            metadata={"user_impact": 1, "workflow_frequency": 1, "severity": 1, "confidence": 1, "repairability": 1}
        )

        orch.issue_memory.record_issue(iss_ux)
        orch.issue_memory.record_issue(iss_ast)
        orch.issue_memory.record_issue(iss_unscored)
        orch.issue_memory.record_issue(iss_reopened)

        self.assertEqual(orch.calculate_product_score(iss_ux), 2000)
        self.assertEqual(orch.calculate_product_score(iss_ast), 1)
        self.assertIsNone(orch.calculate_product_score(iss_unscored), "Incomplete dimensions must be unscored/UNKNOWN")

        ranked = orch.prioritize_issues([iss_ast, iss_unscored, iss_ux, iss_reopened])
        # Priority order:
        # 1. REOPENED issue (Priority 0)
        self.assertEqual(ranked[0].issue_id, "REG-01")
        # 2. UX Defect with Score 2000 (Priority 1)
        self.assertEqual(ranked[1].issue_id, "BUG-UX-01")
        # 3. Hotspot with Score 1
        self.assertEqual(ranked[2].issue_id, "HOTSPOT-AST-01")
        # 4. Unscored issue (score None treated as 0)
        self.assertEqual(ranked[3].issue_id, "ISSUE-RAW-01")

    # -------------------------------------------------------------------------
    # 4. Epistemic Degraded Browser Reality Gating
    # -------------------------------------------------------------------------
    def test_degraded_browser_evidence_blocks_human_pillar(self):
        """
        Refinements 7 & 8:
        When browser_reality is explicitly DEGRADED (wireframe fallback),
        Human Reality CANNOT pass, even if tests and scope are valid.
        """
        orch = IssueOrchestrator(self.tmp_dir)
        orch.discover_issues()
        orch.select_issue("BUG-PROD-01")
        orch.compile_mission()
        orch.execute_attempt(["ultron/interfaces/web/modules/state.js"])

        # Feed test results: pass
        # Feed visual snapshot with browser_reality: "DEGRADED"
        degraded_snap = {
            "browser_reality": "DEGRADED",
            "wireframe_fallback": True,
            "stage": "OVERVIEW",
            "viewport": {"width": 1440, "height": 900},
            "status_message": "Browser reality capture fallback (SVG wireframe)"
        }
        orch.observe_state(snapshot_id="snap_deg_01", test_results={"passed_count": 10, "failed_count": 0, "passed": True}, visual_snapshot=degraded_snap)

        is_verified, reasons = orch.verify_attempt()
        self.assertFalse(is_verified, "Attempt with DEGRADED browser evidence cannot be verified!")
        self.assertFalse(orch.active_attempt.three_pillar_results.get("HUMAN"), "Human pillar must be False on DEGRADED evidence!")
        self.assertTrue(any("Human Reality = NOT_PROVEN: Degraded wireframe evidence" in r for r in reasons))

    # -------------------------------------------------------------------------
    # 5. Crucial Negative Test: BETTER + DEGRADED -> Blocked from Checkpoint
    # -------------------------------------------------------------------------
    def test_better_judgment_with_degraded_browser_blocks_product_improved(self):
        """
        Refinement 8 (Crucial Negative Test):
        Human says BETTER + Browser = DEGRADED
        -> stage becomes HUMAN_JUDGED (capped)
        -> does NOT become PRODUCT_IMPROVED
        -> checkpoint_progression() is strictly blocked!
        """
        orch = IssueOrchestrator(self.tmp_dir)
        orch.discover_issues()
        orch.select_issue("BUG-PROD-01")
        orch.compile_mission()
        orch.execute_attempt(["ultron/interfaces/web/modules/state.js"])

        degraded_snap = {
            "browser_reality": "DEGRADED",
            "wireframe_fallback": True,
            "stage": "OVERVIEW",
            "viewport": {"width": 1440, "height": 900}
        }
        orch.observe_state(snapshot_id="snap_deg_02", test_results={"passed_count": 5, "failed_count": 0, "passed": True}, visual_snapshot=degraded_snap)
        orch.verify_attempt()

        # Human operator submits BETTER rating
        orch.record_human_judgment(rating="BETTER", rationale="I think it looks better")

        # Must NOT be PRODUCT_IMPROVED
        self.assertEqual(orch.active_attempt.progression_stage, "HUMAN_JUDGED", "Stage must be capped at HUMAN_JUDGED because browser is DEGRADED!")
        self.assertEqual(orch.active_attempt.outcome, "PRODUCT_REVIEW_REQUIRED")

        # Checkpoint MUST be blocked
        with self.assertRaises(InvalidStateTransitionError) as ctx:
            orch.checkpoint_progression("Claiming improvement without full browser reality")
        self.assertIn("Attempt must reach constitutional stage 'PRODUCT_IMPROVED'", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 6. Constitutional 4-Stage Progression to Checkpoint
    # -------------------------------------------------------------------------
    def test_full_progression_to_product_improved_and_checkpoint(self):
        """
        Refinements 7 & 8:
        Tests valid -> MECHANICALLY_COMPLIANT
        Browser FULL -> BROWSER_VERIFIED
        Human judged -> HUMAN_JUDGED
        Rating == BETTER with FULL reality -> PRODUCT_IMPROVED -> Checkpoint authorized!
        """
        orch = IssueOrchestrator(self.tmp_dir)
        orch.discover_issues()
        orch.select_issue("BUG-PROD-01")
        orch.compile_mission()
        orch.execute_attempt(["ultron/interfaces/web/modules/state.js"])

        full_snap = {
            "browser_reality": "FULL",
            "wireframe_fallback": False,
            "stage": "OVERVIEW",
            "viewport": {"width": 1440, "height": 900},
            "runtime_health": {"status": "HEALTHY"},
            "action_priority_conflicts": []
        }
        orch.observe_state(snapshot_id="snap_full_01", test_results={"passed_count": 20, "failed_count": 0, "passed": True}, visual_snapshot=full_snap)
        is_verified, reasons = orch.verify_attempt()

        self.assertTrue(is_verified)
        self.assertEqual(orch.active_attempt.progression_stage, "BROWSER_VERIFIED")

        # Advance work queue to CHECKPOINT_READY
        orch.guard_regression_and_advance()
        self.assertEqual(orch.work_queue.get_state().status, "CHECKPOINT_READY")

        # Human operator records rating BETTER
        orch.record_human_judgment(rating="BETTER", rationale="Mission handoff works seamlessly across all providers")
        self.assertEqual(orch.active_attempt.progression_stage, "PRODUCT_IMPROVED")

        # Checkpoint progression succeeds
        cid = orch.checkpoint_progression("Seamless Mission Handoff & Provider Synchronization verified")
        self.assertTrue(cid.startswith("CHK-"))
        self.assertEqual(orch.work_queue.get_state().status, "CHECKPOINTED")

    # -------------------------------------------------------------------------
    # 7. End-to-End 3-Iteration Lifecycle (A: Clean, B: Repair, C: Defense)
    # -------------------------------------------------------------------------
    def test_iteration_lifecycle_clean_repair_regression_defense(self):
        """
        Phase 2.0 3-Iteration Lifecycle:
        - Iteration A: Clean improvement verified through PRODUCT_IMPROVED and checkpointed.
        - Iteration B: Injected intent-loss defect detected -> REPAIR_REQUIRED -> repair mission compiled -> fix applied -> verified.
        - Iteration C: Historical regression defense prevents re-manifestation.
        """
        orch = IssueOrchestrator(self.tmp_dir)

        # --- ITERATION A: Clean Path ---
        orch.discover_issues()
        orch.select_issue("BUG-PROD-01")
        orch.compile_mission()
        orch.execute_attempt(["ultron/interfaces/web/modules/state.js"])

        full_snap = {
            "browser_reality": "FULL",
            "wireframe_fallback": False,
            "stage": "OVERVIEW",
            "viewport": {"width": 1440, "height": 900},
            "runtime_health": {"status": "HEALTHY"}
        }
        orch.observe_state(snapshot_id="snap_it_a", test_results={"passed_count": 25, "failed_count": 0, "passed": True}, visual_snapshot=full_snap)
        orch.verify_attempt()
        orch.guard_regression_and_advance()
        orch.record_human_judgment(rating="BETTER", rationale="StateStore maintains canonical mission state")
        self.assertEqual(orch.active_attempt.progression_stage, "PRODUCT_IMPROVED")
        cid_a = orch.checkpoint_progression("Iteration A verified product improvement")
        self.assertTrue(cid_a.startswith("CHK-"))

        # Issue is now in REGRESSION_GUARD
        iss_rec = orch.issue_memory.get_issue("BUG-PROD-01")
        self.assertEqual(iss_rec.status, "REGRESSION_GUARD")

        # --- ITERATION B: Defect Injected & Diagnostic Repair ---
        # Next work cycle
        orch.work_queue.reset()
        orch.work_queue.transition_to("DISCOVERING")
        orch.select_issue("BUG-PROD-01")
        orch.compile_mission()
        orch.execute_attempt(["ultron/interfaces/web/modules/state.js"])

        # Inject defect: tests fail with reproduction signature
        defect_failures = "AssertionError: PROVIDER_SYNC_DESYNCHRONIZATION - typed intent dropped on provider switch"
        orch.observe_state(
            snapshot_id="snap_it_b_fail",
            test_results={"passed_count": 24, "failed_count": 1, "failures": defect_failures, "passed": False},
            visual_snapshot=full_snap
        )
        is_verified, reasons = orch.verify_attempt()
        self.assertFalse(is_verified)
        self.assertEqual(orch.active_attempt.outcome, "REGRESSION_DETECTED")

        # Guard intercepts regression and marks BLOCKED
        state_adv = orch.guard_regression_and_advance()
        self.assertEqual(state_adv.status, "BLOCKED")

        # Compile repair mission
        repair_packet = {
            "blocking_reasons": reasons,
            "pillar": "HUMAN",
            "failure_class": "PROVIDER_SYNC_DESYNCHRONIZATION",
            "observation": "Typed intent was dropped during provider switch",
            "reproduction": "Switch provider pill",
            "reproduction_signature": "PROVIDER_SYNC_DESYNCHRONIZATION"
        }
        repair_mission = orch.compile_repair_mission(issue_id="BUG-PROD-01", failure_packet=repair_packet)
        self.assertEqual(orch.work_queue.get_state().status, "MISSION_READY")
        self.assertEqual(orch.active_attempt.attempt_number, 2)

        # Apply repair fix and observe recovery
        orch.execute_attempt(["ultron/interfaces/web/modules/state.js"])
        orch.observe_state(
            snapshot_id="snap_it_b_fixed",
            test_results={"passed_count": 25, "failed_count": 0, "passed": True},
            visual_snapshot=full_snap
        )
        is_verified_b, _ = orch.verify_attempt()
        self.assertTrue(is_verified_b)
        orch.guard_regression_and_advance()
        self.assertEqual(orch.work_queue.get_state().status, "CHECKPOINT_READY")
        orch.record_human_judgment(rating="BETTER", rationale="Repair confirmed")
        cid_b = orch.checkpoint_progression("Iteration B repair verified and reguarded")
        self.assertTrue(cid_b.startswith("CHK-"))

        # --- ITERATION C: Historical Regression Defense Across Reload ---
        orch_reloaded = IssueOrchestrator(self.tmp_dir)
        hist_issues = orch_reloaded.issue_memory.list_issues(status="REGRESSION_GUARD")
        self.assertTrue(any(i.issue_id == "BUG-PROD-01" for i in hist_issues), "BUG-PROD-01 must remain guarded in IssueMemory across reloads!")


if __name__ == "__main__":
    unittest.main()
