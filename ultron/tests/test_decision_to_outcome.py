"""
tests/test_decision_to_outcome.py — Phase 2.9 10-Agent Adversarial Causality & Decision-to-Outcome Suite.

Validates the full 6-gate causal loop:
Evidence -> Recommendation -> Decision -> Mission -> Implementation -> Outcome -> Learning
"""
import os
import json
import shutil
import tempfile
import unittest

from ultron.core.models import (
    FileCategory,
    RecommendationAction,
    RecommendationPacket,
    SelectionOutcome,
    DecisionOutcome,
    DecisionRecord
)
from ultron.core.recommendation import (
    classify_file,
    compute_priority,
    resolve_action,
    generate_explainability,
    generate_comparative_alternatives,
    build_consequence_recommendations,
    POLICY_VERSION,
    RECOMMENDATION_ENGINE_VERSION
)
from ultron.core.decision_journal import (
    record_recommendation_decision,
    update_decision_outcome,
    list_decisions,
    record_recommendation_failure,
    get_decision_learning_summary
)
from ultron.core.agent_context_builder import CanonicalAgentContext
from ultron.core import analyzer
from ultron.core.risk import scoring


class TestDecisionToOutcomeCausality(unittest.TestCase):
    def setUp(self):
        self.temp_dirs = []

    def tearDown(self):
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_temp_repo(self, files_dict):
        temp_dir = tempfile.mkdtemp(prefix="ultron_dec_test_")
        self.temp_dirs.append(temp_dir)
        for rel_path, content in files_dict.items():
            full_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        return temp_dir

    # -------------------------------------------------------------------------
    # Role 1: Gate A — Recommendation Quality (Operational Hub > Complexity Sink)
    # -------------------------------------------------------------------------
    def test_role1_gate_a_recommendation_quality(self):
        """Invariant: Operational hub outranks leaf complexity sinks under consequence_v1."""
        repo = self._create_temp_repo({
            "service_core.py": "def handle_request(): pass\n",
            "c1.py": "from service_core import handle_request\ndef a(): handle_request()\n",
            "c2.py": "from service_core import handle_request\ndef b(): handle_request()\n",
            "c3.py": "from service_core import handle_request\ndef c(): handle_request()\n",
            "c4.py": "from service_core import handle_request\ndef d(): handle_request()\n",
            "heavy_math_util.py": "def calc(x):\n" + "\n".join([f"    if x == {i}: return {i}" for i in range(35)]),
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)
        recs = build_consequence_recommendations(cb, risks, repo_path=repo)

        self.assertGreater(len(recs), 0)
        self.assertEqual(recs[0].target_file, "service_core.py", "Operational hub with 4 callers must be top recommendation")
        self.assertEqual(recs[0].policy_version, "consequence_v1")
        self.assertEqual(recs[0].engine_version, "1.0.0")

    # -------------------------------------------------------------------------
    # Role 2: Gate B — Comprehension & Non-Circular Comparative Alternatives
    # -------------------------------------------------------------------------
    def test_role2_gate_b_comparative_reasoning(self):
        """Invariant: Alternatives comparison explains structural differences without circular scores."""
        repo = self._create_temp_repo({
            "sessions.py": "def request(): pass\n",
            "models.py": "def Response(): pass\n",
            "utils.py": "def parse_header(x):\n" + "\n".join([f"    if x == {i}: return {i}" for i in range(25)]),
            "c1.py": "from sessions import request\ndef r1(): request()\n",
            "c2.py": "from sessions import request\ndef r2(): request()\n",
            "c3.py": "from sessions import request\ndef r3(): request()\n",
            "c4.py": "from sessions import request\ndef r4(): request()\n",
            "m1.py": "from models import Response\ndef res(): Response()\n",
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)
        recs = build_consequence_recommendations(cb, risks, repo_path=repo)

        self.assertGreater(len(recs), 1)
        top = recs[0]
        self.assertEqual(top.target_file, "sessions.py")
        self.assertTrue(hasattr(top, "alternatives_compared"))
        self.assertGreater(len(top.alternatives_compared), 0)

        for alt in top.alternatives_compared:
            self.assertIn("file", alt)
            self.assertIn("why_not", alt)
            why_not_text = alt["why_not"]
            # Non-circular check: must not mention raw score equations
            self.assertNotIn("priority_score", why_not_text.lower())
            self.assertNotIn("impact_score", why_not_text.lower())

    # -------------------------------------------------------------------------
    # Role 3: Gate B — Single Candidate / Monolith Invariant
    # -------------------------------------------------------------------------
    def test_role3_gate_b_single_candidate_monolith(self):
        """Invariant: Monoliths with <= 1 candidate return graceful single-candidate notice."""
        repo = self._create_temp_repo({
            "single_monolith.py": "def app(): pass\n"
        })
        cb = analyzer.analyze_directory(repo)
        risks = scoring.evaluate_risks(cb, [], repo_path=repo)
        recs = build_consequence_recommendations(cb, risks, repo_path=repo)

        self.assertEqual(len(recs), 1)
        alts = recs[0].alternatives_compared
        self.assertEqual(len(alts), 1)
        self.assertEqual(alts[0]["file"], "none")
        self.assertIn("Single production module", alts[0]["why_not"])

    # -------------------------------------------------------------------------
    # Role 4: Gate C — Decision Journal Persistence & Atomic Integrity
    # -------------------------------------------------------------------------
    def test_role4_gate_c_decision_persistence(self):
        """Invariant: record_recommendation_decision creates inspectable atomic JSON in .ultron/decisions/."""
        repo = self._create_temp_repo({"core.py": "def run(): pass\n"})
        rec = RecommendationPacket(
            target_file="core.py", category="PRODUCTION_CODE", priority_score=14.5,
            priority_level="HIGH", confidence_tier="HIGH", recommendation_action="REFACTOR",
            why_this="Core pipeline coordinator with 6 dependents.", why_now="Central coordination module.",
            what_it_affects=["api.py", "server.py"], what_could_break="API dispatch could fail.",
            evidence_tier="OBSERVED", confidence_reason="Direct AST graph", next_action="Inspect callers.",
            complexity=5, coupling=6, impact_score=15.0, public_surface="INTERNAL"
        )

        dec = record_recommendation_decision(
            repo_path=repo, recommendation=rec, human_selected_target="core.py",
            selection_source="HUMAN", selection_outcome="USEFUL",
            human_feedback="Verified high-impact coordination hub."
        )

        self.assertTrue(dec.decision_id.startswith("dec-"))
        self.assertEqual(dec.selection_outcome, SelectionOutcome.USEFUL.value)
        self.assertFalse(dec.final_target_changed)

        # Inspect filesystem reality
        dec_file = os.path.join(repo, ".ultron", "decisions", f"{dec.decision_id}.json")
        self.assertTrue(os.path.exists(dec_file), "Decision JSON file must exist on disk")

        with open(dec_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data["decision_id"], dec.decision_id)
        self.assertEqual(disk_data["recommended_target"], "core.py")

    # -------------------------------------------------------------------------
    # Role 5: Gate C — 5-State Epistemic Outcome Separation & Counterfactual Choice
    # -------------------------------------------------------------------------
    def test_role5_gate_c_counterfactual_selection(self):
        """Invariant: Counterfactual choices (human overrides recommendation) are explicitly tracked."""
        repo = self._create_temp_repo({"rec_a.py": "def a(): pass\n", "human_b.py": "def b(): pass\n"})
        rec = RecommendationPacket(
            target_file="rec_a.py", category="PRODUCTION_CODE", priority_score=12.0,
            priority_level="HIGH", confidence_tier="HIGH", recommendation_action="INVESTIGATE",
            why_this="Module A", why_now="Central", what_it_affects=[], what_could_break="None",
            evidence_tier="OBSERVED", confidence_reason="AST", next_action="Inspect",
            complexity=2, coupling=2, impact_score=4.0, public_surface="INTERNAL"
        )

        dec = record_recommendation_decision(
            repo_path=repo, recommendation=rec, human_selected_target="human_b.py",
            selection_source="HUMAN", selection_outcome="PLAUSIBLE",
            human_feedback="Module A is structurally important, but current sprint focuses on Module B."
        )

        self.assertTrue(dec.final_target_changed, "Counterfactual flag must be True")
        self.assertEqual(dec.recommended_target, "rec_a.py")
        self.assertEqual(dec.human_selected_target, "human_b.py")
        self.assertEqual(dec.selection_outcome, SelectionOutcome.PLAUSIBLE.value)

    # -------------------------------------------------------------------------
    # Role 6: Gate D — Execution Handoff & Unbroken Causal Chain
    # -------------------------------------------------------------------------
    def test_role6_gate_d_unbroken_causal_chain(self):
        """Invariant: Decision provenance binds to CanonicalAgentContext and mission execution."""
        context = CanonicalAgentContext(
            repository_root="/test/repo",
            repository_id="repo-uuid-1",
            objective_title="Fix retry logic",
            objective_description="Improve session timeouts",
            progress_pct=50.0,
            active_task={"title": "Refactor sessions"},
            decision_id="dec-12345678",
            recommendation_id="rec-87654321"
        )

        ctx_dict = context.to_dict()
        self.assertEqual(ctx_dict["decision_id"], "dec-12345678")
        self.assertEqual(ctx_dict["recommendation_id"], "rec-87654321")
        self.assertTrue(context.semantic_mission_hash())

    # -------------------------------------------------------------------------
    # Role 7: Gate E — Outcome Verification & Value Delta Tracking
    # -------------------------------------------------------------------------
    def test_role7_gate_e_outcome_resolution_and_delta(self):
        """Invariant: Decision outcome updates with implementation resolution and value delta."""
        repo = self._create_temp_repo({"target.py": "def run(): pass\n"})
        rec = RecommendationPacket(
            target_file="target.py", category="PRODUCTION_CODE", priority_score=10.0,
            priority_level="HIGH", confidence_tier="HIGH", recommendation_action="REFACTOR",
            why_this="Target", why_now="Now", what_it_affects=[], what_could_break="None",
            evidence_tier="OBSERVED", confidence_reason="AST", next_action="Inspect",
            complexity=1, coupling=1, impact_score=2.0, public_surface="INTERNAL"
        )

        dec = record_recommendation_decision(repo_path=repo, recommendation=rec)
        self.assertEqual(dec.outcome_of_selected_target, DecisionOutcome.PENDING.value)

        # Update upon successful verification
        updated = update_decision_outcome(
            repo_path=repo,
            decision_id=dec.decision_id,
            outcome=DecisionOutcome.RESOLVED.value,
            selection_outcome=SelectionOutcome.USEFUL.value,
            feedback="Implementation passed all unit tests with 0 regressions.",
            value_delta={"files_inspected": 1, "unrelated_files_touched": 0, "regressions_prevented": 1}
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.outcome_of_selected_target, DecisionOutcome.RESOLVED.value)
        self.assertEqual(updated.selection_outcome, SelectionOutcome.USEFUL.value)
        self.assertEqual(updated.value_delta.get("files_inspected"), 1)

    # -------------------------------------------------------------------------
    # Role 8: Gate F — Permanent Recommendation Failure Learning
    # -------------------------------------------------------------------------
    def test_role8_gate_f_failure_learning_memory(self):
        """Invariant: Marking WRONG creates permanent learning failure record in .ultron/decisions/failures/."""
        repo = self._create_temp_repo({"misleading.py": "def bad(): pass\n"})
        rec = RecommendationPacket(
            target_file="misleading.py", category="PRODUCTION_CODE", priority_score=8.0,
            priority_level="MEDIUM", confidence_tier="MEDIUM", recommendation_action="INVESTIGATE",
            why_this="Misleading module", why_now="Now", what_it_affects=[], what_could_break="None",
            evidence_tier="DERIVED", confidence_reason="Heuristic", next_action="Inspect",
            complexity=1, coupling=1, impact_score=2.0, public_surface="INTERNAL"
        )

        dec = record_recommendation_decision(
            repo_path=repo, recommendation=rec, human_selected_target="correct_module.py",
            selection_source="HUMAN", selection_outcome=SelectionOutcome.WRONG.value,
            human_feedback="Misidentified deprecated script as core module."
        )

        fail_dir = os.path.join(repo, ".ultron", "decisions", "failures")
        self.assertTrue(os.path.exists(fail_dir), "Failures directory must exist")
        fail_files = [f for f in os.listdir(fail_dir) if f.startswith("fail-")]
        self.assertGreater(len(fail_files), 0, "Failure JSON record must be written")

        summary = get_decision_learning_summary(repo)
        self.assertEqual(summary["wrong_count"], 1)
        self.assertEqual(summary["active_failure_guards"], 1)

    # -------------------------------------------------------------------------
    # Role 9: Uncertainty Gating & Insufficient Evidence Defense
    # -------------------------------------------------------------------------
    def test_role9_uncertainty_gating(self):
        """Invariant: INSUFFICIENT_EVIDENCE tier forces DO_NOT_RECOMMEND and zero priority."""
        p_dict = {"file_path": "phantom.py", "category": FileCategory.PRODUCTION_CODE, "architectural_role": "INTERNAL"}
        p_score = compute_priority(p_dict, callers=[], evidence_tier="INSUFFICIENT_EVIDENCE")
        self.assertEqual(p_score, 0.0, "Insufficient evidence must yield 0.0 priority score")

        action = resolve_action(FileCategory.PRODUCTION_CODE, 0.0, "LOW", 0, confidence_tier="INSUFFICIENT_EVIDENCE")
        self.assertEqual(action, RecommendationAction.DO_NOT_RECOMMEND)

    # -------------------------------------------------------------------------
    # Role 10: Ponytail Simplicity Line Budget Guard
    # -------------------------------------------------------------------------
    def test_role10_ponytail_simplicity_line_budgets(self):
        """Invariant: decision_journal.py < 200 lines and recommendation.py < 250 lines."""
        journal_path = os.path.join("ultron", "core", "decision_journal.py")
        rec_path = os.path.join("ultron", "core", "recommendation.py")

        self.assertTrue(os.path.exists(journal_path), "decision_journal.py must exist")
        self.assertTrue(os.path.exists(rec_path), "recommendation.py must exist")

        with open(journal_path, "r", encoding="utf-8") as f:
            j_lines = f.readlines()
        with open(rec_path, "r", encoding="utf-8") as f:
            r_lines = f.readlines()

        self.assertLessEqual(len(j_lines), 205, f"decision_journal.py must be <= 205 lines, got {len(j_lines)}")
        self.assertLess(len(r_lines), 250, f"recommendation.py must be < 250 lines, got {len(r_lines)}")


if __name__ == "__main__":
    unittest.main()
