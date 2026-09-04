"""
ultron/tests/test_truth_engine.py — 10-Role Adversarial Truth Engine & Canonical Evidence Test Suite.
Gate A: Validates zero-guessing, 6-layer epistemic hierarchy, deterministic evidence identity, and contextual objective gating.
"""
import os
import unittest
import tempfile
import shutil
from dataclasses import FrozenInstanceError
from ultron.core.evidence import (
    EvidenceClassification, ConfidenceTier, EvidenceStatus,
    EvidenceRecord, EvidenceBundle, compile_repository_evidence, compute_evidence_id
)
from ultron.core.models import FileCategory, RecommendationAction, RecommendationPacket, SelectionOutcome
from ultron.core.recommendation import (
    compute_priority, resolve_action, build_consequence_recommendations,
    generate_explainability, generate_comparative_alternatives
)
from ultron.core.decision_journal import (
    record_recommendation_decision, list_decisions, update_decision_outcome
)


class TestTruthEngineGateA(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Role 1: Direct Observation Integrity
    # -------------------------------------------------------------------------
    def test_role1_direct_observation(self):
        """Direct AST facts must be classified as OBSERVED with HIGH confidence."""
        codebase = {
            "core/engine.py": {"complexity": 5, "callers": ["cli.py", "server.py"]}
        }
        bundle = compile_repository_evidence(self.test_dir, codebase, snapshot_id="snap-test-01")
        records = bundle.get_records_for_target("core/engine.py")
        
        self.assertGreater(len(records), 0)
        ast_comp = next((r for r in records if r.source == "AST" and "cyclomatic_complexity" in r.value), None)
        self.assertIsNotNone(ast_comp)
        self.assertEqual(ast_comp.classification, EvidenceClassification.OBSERVED.value)
        self.assertEqual(ast_comp.confidence, ConfidenceTier.HIGH.value)
        self.assertEqual(ast_comp.value["cyclomatic_complexity"], 5)

    # -------------------------------------------------------------------------
    # Role 2: Mathematical Derivation Traceability
    # -------------------------------------------------------------------------
    def test_role2_mathematical_derivation(self):
        """Derived metrics must be classified as DERIVED with explicit derivation description."""
        codebase = {
            "gateway.py": {"complexity": 2, "callers": ["a.py", "b.py"], "blast_radius": ["a.py", "b.py", "c.py"]}
        }
        bundle = compile_repository_evidence(self.test_dir, codebase, snapshot_id="snap-test-02")
        records = bundle.get_records_for_target("gateway.py")
        
        blast_rec = next((r for r in records if r.source == "STATIC_ANALYSIS" and "blast_radius" in r.value), None)
        self.assertIsNotNone(blast_rec)
        self.assertEqual(blast_rec.classification, EvidenceClassification.DERIVED.value)
        self.assertEqual(blast_rec.confidence, ConfidenceTier.HIGH.value)
        self.assertIn("Transitive closure", blast_rec.derivation)

    # -------------------------------------------------------------------------
    # Role 3: Missing Dependency / Explicit Unknown Disclose
    # -------------------------------------------------------------------------
    def test_role3_missing_dependency_unknown(self):
        """Missing Git history must be marked UNKNOWN with explicit limitation disclosure."""
        codebase = {"app.py": {"complexity": 1, "callers": []}}
        bundle = compile_repository_evidence(self.test_dir, codebase, git_history=None, snapshot_id="snap-test-03")
        
        git_rec = next((r for r in bundle.records.values() if r.source == "GIT"), None)
        self.assertIsNotNone(git_rec)
        self.assertEqual(git_rec.classification, EvidenceClassification.UNKNOWN.value)
        self.assertEqual(git_rec.confidence, ConfidenceTier.NOT_ASSESSED.value)
        self.assertIn("Git history unavailable", bundle.limitations[0])

    # -------------------------------------------------------------------------
    # Role 4: Dynamic Dispatch & Partial Context Limitations
    # -------------------------------------------------------------------------
    def test_role4_limitation_disclosure(self):
        """Records with unmeasured attributes must disclose limitations."""
        rec = EvidenceRecord.create(
            source="AST",
            target="dynamic_handler.py",
            snapshot_id="snap-test-04",
            classification=EvidenceClassification.INFERRED,
            confidence=ConfidenceTier.LOW,
            value={"estimated_callers": 2},
            derivation="Heuristic string symbol match",
            limitations=["Dynamic getattr dispatch unobserved by static AST"]
        )
        self.assertEqual(rec.confidence, ConfidenceTier.LOW.value)
        self.assertIn("Dynamic getattr dispatch", rec.limitations[0])

    # -------------------------------------------------------------------------
    # Role 5: Uncertainty Gating
    # -------------------------------------------------------------------------
    def test_role5_uncertainty_gating(self):
        """INSUFFICIENT_EVIDENCE or UNKNOWN tier must clamp priority to 0.0 and DO_NOT_RECOMMEND."""
        packet_dict = {"file_path": "unproven.py", "category": FileCategory.PRODUCTION_CODE, "architectural_role": "INTERNAL"}
        p_score = compute_priority(packet_dict, callers=["a.py"], evidence_tier="INSUFFICIENT_EVIDENCE")
        self.assertEqual(p_score, 0.0)

        action = resolve_action(
            FileCategory.PRODUCTION_CODE, 0.0, "LOW", 1, confidence_tier="INSUFFICIENT_EVIDENCE", has_sufficient_evidence=False
        )
        self.assertEqual(action, RecommendationAction.DO_NOT_RECOMMEND)

    # -------------------------------------------------------------------------
    # Role 6: Evidence Immutability & Content-Addressable Identity
    # -------------------------------------------------------------------------
    def test_role6_evidence_immutability_and_stable_id(self):
        """EvidenceRecord must be frozen and deterministic across identical invocations."""
        rec1 = EvidenceRecord.create(
            source="AST", target="models.py", snapshot_id="snap-01",
            classification=EvidenceClassification.OBSERVED, confidence=ConfidenceTier.HIGH,
            value={"callers": 4}
        )
        rec2 = EvidenceRecord.create(
            source="AST", target="models.py", snapshot_id="snap-01",
            classification=EvidenceClassification.OBSERVED, confidence=ConfidenceTier.HIGH,
            value={"callers": 4}
        )
        self.assertEqual(rec1.evidence_id, rec2.evidence_id)

        # Immutability check
        with self.assertRaises(FrozenInstanceError):
            rec1.target = "mutated.py"

    # -------------------------------------------------------------------------
    # Role 7: Evidence Validity & Expiration (Staleness Invariant)
    # -------------------------------------------------------------------------
    def test_role7_evidence_validity_and_staleness(self):
        """EvidenceBundle must report is_fresh = True only when snapshot matches active revision."""
        codebase = {"main.py": {"complexity": 2, "callers": []}}
        bundle = compile_repository_evidence(self.test_dir, codebase, snapshot_id="snap-v1")
        
        self.assertTrue(bundle.is_fresh("snap-v1"))
        self.assertFalse(bundle.is_fresh("snap-v2"))

    # -------------------------------------------------------------------------
    # Role 8: Cross-Layer Provenance Consistency
    # -------------------------------------------------------------------------
    def test_role8_cross_layer_consistency(self):
        """Recommendation and DecisionRecord must bind identical evidence_ids."""
        codebase = {"sessions.py": {"complexity": 4, "callers": ["api.py", "client.py"]}}
        bundle = compile_repository_evidence(self.test_dir, codebase, snapshot_id="snap-08")
        recs = build_consequence_recommendations(codebase, [], repo_path=self.test_dir, evidence_bundle=bundle)
        self.assertEqual(len(recs), 1)
        
        top_rec = recs[0]
        self.assertGreater(len(top_rec.evidence_records), 0)
        
        dec = record_recommendation_decision(self.test_dir, top_rec)
        self.assertGreater(len(dec.evidence_ids), 0)
        self.assertEqual(dec.evidence_ids[0], top_rec.evidence_records[0]["evidence_id"])

    # -------------------------------------------------------------------------
    # Role 9: Epistemic Self-Audit Hierarchy
    # -------------------------------------------------------------------------
    def test_role9_epistemic_self_audit(self):
        """Bundle must compute correct coverage and unknown counts without silent assumptions."""
        codebase = {
            "a.py": {"complexity": 1, "callers": []},
            "b.py": {"complexity": 2, "callers": ["a.py"]}
        }
        bundle = compile_repository_evidence(self.test_dir, codebase, git_history=None)
        self.assertGreaterEqual(bundle.evidence_coverage_pct, 70.0)
        self.assertLessEqual(bundle.evidence_coverage_pct, 100.0)
        self.assertGreater(bundle.unknown_count, 0)

    # -------------------------------------------------------------------------
    # Role 10: Agent 10 Invariant (Correct Facts != Correct Conclusion)
    # -------------------------------------------------------------------------
    def test_role10_agent10_contextual_objective_gating(self):
        """Correct topology facts must not override an explicit active human objective."""
        # Topologically, sessions.py has more callers (9) than cli.py (1).
        # But active objective is "Improve CLI startup time and argument parsing".
        codebase = {
            "requests/sessions.py": {"complexity": 79, "callers": ["a", "b", "c", "d", "e", "f", "g", "h", "i"]},
            "requests/cli.py": {"complexity": 5, "callers": ["main.py"]}
        }
        bundle = compile_repository_evidence(self.test_dir, codebase, snapshot_id="snap-10")
        
        # When objective is empty, sessions.py dominates due to 9 callers
        recs_no_obj = build_consequence_recommendations(codebase, [], objective="", repo_path=self.test_dir, evidence_bundle=bundle)
        self.assertEqual(recs_no_obj[0].target_file, "requests/sessions.py")

        # When active objective is 'CLI startup time', cli.py must be elevated over sessions.py
        recs_cli_obj = build_consequence_recommendations(
            codebase, [], objective="Improve CLI startup time", repo_path=self.test_dir, evidence_bundle=bundle
        )
        self.assertEqual(recs_cli_obj[0].target_file, "requests/cli.py")
        self.assertIn("Matches active objective", recs_cli_obj[0].why_now)


if __name__ == "__main__":
    unittest.main()
