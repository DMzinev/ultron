"""
ultron/tests/test_signal_quality.py

Baseline behavioral tests for signal quality across synthetic fixture repositories.
Documents today's behavior as an executable specification per docs/AGENT_EXECUTION_PLAN.md Task A1.

Fixtures:
- clean_repo: 8 files, low complexity, shallow imports, no cycles.
- tangled_repo: 8 files, one 400-line god module, 3-file import cycle, deep fan-in.
- mixed_repo: 12 files, 2 genuinely risky, 10 benign.
"""

import os
import unittest

from ultron.core.pipeline.discovery import discover
from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.pipeline.orchestrator import analyze_repository
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.evolution.engine import EvolutionEngine

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))


def _analyze_fixture(fixture_name):
    """Helper to discover, extract facts, and evaluate risks on a fixture repo."""
    repo_path = os.path.join(FIXTURES_DIR, fixture_name)
    files = discover(repo_path)
    codebase = analyzer.analyze_directory(repo_path)
    risks = scoring.evaluate_risks(codebase, files, repo_path=repo_path)
    return files, codebase, risks, repo_path


def _get_health_score(fixture_name):
    """Helper to run full orchestrator pipeline and compute health score."""
    repo_path = os.path.join(FIXTURES_DIR, fixture_name)
    uuid = analyze_repository(repo_path, force=True)
    db_path = os.path.join(repo_path, ".ultron", "repository.db")
    if not os.path.exists(db_path):
        return None
    store = RepositoryStore(db_path)
    try:
        meta = store.get_metadata()
        if not meta or not meta.latest_analysis_run_id:
            return None
        run_id = meta.latest_analysis_run_id
        health_run = EvolutionEngine.evaluate_health_score(store, run_id)
        score = round(
            (health_run.architecture_stability * 0.4 +
             health_run.rule_compliance * 0.4 +
             health_run.complexity_trend * 0.2) * 100, 1
        )
        return score
    finally:
        store.close()


class TestCleanRepoSignalQuality(unittest.TestCase):
    """Distribution properties for clean_repo (8 files, low complexity, shallow imports, no cycles)."""

    def setUp(self):
        self.files, self.codebase, self.risks, self.repo_path = _analyze_fixture("clean_repo")

    def test_clean_repo_file_count(self):
        """clean_repo fixture must contain exactly 8 files."""
        self.assertEqual(len(self.files), 8, f"Expected 8 files in clean_repo, got {len(self.files)}")

    def test_clean_repo_has_zero_high_risks(self):
        """A genuinely clean repository must produce 0 HIGH-risk files."""
        high_files = [r.file_path for r in self.risks if r.level == "HIGH"]
        self.assertEqual(
            len(high_files), 0,
            f"Clean repo should have 0 HIGH files, but found {len(high_files)}: {high_files}"
        )

    def test_clean_repo_health_score(self):
        """A clean repo must have a healthy score (>= 80)."""
        score = _get_health_score("clean_repo")
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 80.0, f"Clean repo health score {score} is below healthy threshold (80.0)")


class TestTangledRepoSignalQuality(unittest.TestCase):
    """Distribution properties for tangled_repo (8 files, 400-line god module, 3-file cycle, deep fan-in)."""

    def setUp(self):
        self.files, self.codebase, self.risks, self.repo_path = _analyze_fixture("tangled_repo")

    def test_tangled_repo_file_count(self):
        """tangled_repo fixture must contain exactly 8 files."""
        self.assertEqual(len(self.files), 8, f"Expected 8 files in tangled_repo, got {len(self.files)}")

    def test_god_module_ranks_first(self):
        """The 400-line god module with deep fan-in must rank at the top of the risk distribution."""
        sorted_risks = sorted(self.risks, key=lambda r: r.impact_score, reverse=True)
        top_file = sorted_risks[0].file_path
        self.assertEqual(top_file, "god_module.py", f"Expected god_module.py at rank 1, got {top_file}")
        self.assertEqual(sorted_risks[0].level, "HIGH")

    def test_god_module_and_every_cycle_member_rank_in_top_3(self):
        """The god module and every member of the 3-file cycle must rank in the top 3."""
        sorted_risks = sorted(self.risks, key=lambda r: r.impact_score, reverse=True)
        top_3_files = {r.file_path for r in sorted_risks[:3]}
        expected_top = {"god_module.py", "cycle_b.py", "cycle_c.py"}
        self.assertEqual(
            top_3_files, expected_top,
            f"Expected top 3 to be {expected_top}, but got {top_3_files}"
        )

    def test_tangled_repo_invariants_and_relative_mitigation(self):
        """tangled_repo must enforce distribution caps and relative blast-radius mitigation."""
        high_files = [r for r in self.risks if r.level == "HIGH"]
        med_files = [r for r in self.risks if r.level == "MEDIUM"]
        self.assertLessEqual(len(high_files), 2, "HIGH files must be <= 15% (<= 2 for N=8)")
        self.assertLessEqual(len(high_files) + len(med_files), 4, "HIGH+MED files must be <= 45% (<= 4 for N=8)")
        for h in high_files:
            self.assertIn("in the top", h.mitigation)
            self.assertNotIn("Threshold:", h.mitigation)

    def test_tangled_repo_health_score_calibrated(self):
        """Tangled repo with god module and import cycle must score <= 40 (degraded/critical)."""
        score = _get_health_score("tangled_repo")
        self.assertIsNotNone(score)
        self.assertLessEqual(
            score, 40.0,
            f"Tangled repo should score <= 40.0, but got uncalibrated score: {score}"
        )
        band = EvolutionEngine.get_health_band(score)
        self.assertIn(band, ("critical", "degraded"))
        sub_scores = {"architecture_stability": 0.2, "rule_compliance": 0.17, "risk_distribution": 0.375}
        explanation = EvolutionEngine.format_health_explanation(score, sub_scores)
        self.assertIn("Repository health is rated", explanation)
        self.assertIn("Architecture Stability:", explanation)


class TestMixedRepoSignalQuality(unittest.TestCase):
    """Distribution properties for mixed_repo (12 files, 2 genuinely risky, 10 benign)."""

    def setUp(self):
        self.files, self.codebase, self.risks, self.repo_path = _analyze_fixture("mixed_repo")

    def test_mixed_repo_file_count(self):
        """mixed_repo fixture must contain exactly 12 files."""
        self.assertEqual(len(self.files), 12, f"Expected 12 files in mixed_repo, got {len(self.files)}")

    def test_exactly_planted_files_are_high(self):
        """Exactly the 2 planted high-complexity files must be labeled HIGH."""
        high_files = {r.file_path for r in self.risks if r.level == "HIGH"}
        expected_high = {"risky_core.py", "risky_dispatcher.py"}
        self.assertEqual(
            high_files, expected_high,
            f"Expected exactly {expected_high} to be HIGH, got {high_files}"
        )

    def test_benign_files_not_high(self):
        """None of the 10 benign files should be labeled HIGH."""
        benign_high = [
            r.file_path for r in self.risks
            if r.level == "HIGH" and r.file_path not in {"risky_core.py", "risky_dispatcher.py"}
        ]
        self.assertEqual(benign_high, [], f"Benign files falsely marked HIGH: {benign_high}")

    def test_risky_files_top_ranks(self):
        """Planted risky files must have the highest impact scores in the repository."""
        sorted_risks = sorted(self.risks, key=lambda r: r.impact_score, reverse=True)
        top_2_files = {sorted_risks[0].file_path, sorted_risks[1].file_path}
        expected_top = {"risky_core.py", "risky_dispatcher.py"}
        self.assertEqual(top_2_files, expected_top, f"Expected top 2 to be {expected_top}, got {top_2_files}")

    def test_mixed_repo_invariants_and_relative_mitigation(self):
        """mixed_repo must enforce distribution caps and relative blast-radius mitigation."""
        high_files = [r for r in self.risks if r.level == "HIGH"]
        med_files = [r for r in self.risks if r.level == "MEDIUM"]
        self.assertLessEqual(len(high_files), 2, "HIGH files must be <= 15% (<= 2 for N=12)")
        self.assertLessEqual(len(high_files) + len(med_files), 6, "HIGH+MED files must be <= 45% (<= 6 for N=12)")
        for h in high_files:
            self.assertIn("in the top", h.mitigation)
            self.assertNotIn("Threshold:", h.mitigation)


class TestScoringEdgeCases(unittest.TestCase):
    """Zero and boundary state tests for risk scoring engine."""

    def test_empty_codebase_returns_empty_list(self):
        """Empty codebase must return empty risk list without ZeroDivisionError."""
        self.assertEqual(scoring.evaluate_risks({}, []), [])

    def test_empty_codebase_with_targets_returns_empty_list(self):
        """Empty codebase with target files must return empty list."""
        self.assertEqual(scoring.evaluate_risks({}, ["nonexistent.py"]), [])

    def test_nonexistent_target_returns_empty_list(self):
        """Target files not present in codebase must return empty list."""
        codebase = {"a.py": {"imports": [], "definitions": []}}
        self.assertEqual(scoring.evaluate_risks(codebase, ["b.py"]), [])


if __name__ == "__main__":
    unittest.main()
