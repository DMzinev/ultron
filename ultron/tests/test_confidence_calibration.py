"""
ultron/tests/test_confidence_calibration.py

Automated unit test suite for Task P2-C1 per docs/AGENT_EXECUTION_PLAN_PHASE2.md:
"Verify the 4-Signal Confidence Weights Empirically"

Asserts:
1. Confidence weights sum exactly to 1.00.
2. Calibration documentation exists and contains empirical correlation, case studies, and Truth Engine framework.
3. Ground-truth fixture bounds (clean_repo: 0 HIGH, tangled_repo: god_module rank 1 HIGH, mixed_repo: 2 planted HIGH).
4. Honest confidence degradation when churn and coverage signals are missing.
5. Epistemic Truth Engine categories (OBSERVED, DERIVED, INFERRED, VERIFIED) declared and propagated.
"""

import os
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from ultron.core.risk.scoring import (
    CONFIDENCE_WEIGHTS,
    CONFIDENCE_METADATA,
    evaluate_risks
)
from ultron.core.analyzer import analyze_directory


class TestConfidenceCalibration(unittest.TestCase):
    """Hermetic unit tests enforcing empirical calibration, mathematical bounds, and epistemic honesty."""

    def setUp(self):
        self.fixtures_dir = os.path.join(REPO_ROOT, "ultron", "tests", "fixtures")

    def test_confidence_weights_sum_to_one(self):
        """Assert the 4 signal confidence weights sum to exactly 1.00."""
        expected_keys = {"ast", "coupling", "churn", "coverage"}
        self.assertEqual(set(CONFIDENCE_WEIGHTS.keys()), expected_keys)

        total_weight = sum(CONFIDENCE_WEIGHTS.values())
        self.assertAlmostEqual(total_weight, 1.0, places=6, msg="Confidence weights must sum to 1.00")
        self.assertEqual(CONFIDENCE_WEIGHTS["ast"], 0.35)
        self.assertEqual(CONFIDENCE_WEIGHTS["coupling"], 0.25)
        self.assertEqual(CONFIDENCE_WEIGHTS["churn"], 0.15)
        self.assertEqual(CONFIDENCE_WEIGHTS["coverage"], 0.25)

    def test_calibration_documentation_present(self):
        """Assert calibration document exists with empirical case study, fixture validation, and limitations."""
        doc_path = os.path.join(REPO_ROOT, "docs", "calibration", "CONFIDENCE_WEIGHT_CALIBRATION.md")
        self.assertTrue(os.path.isfile(doc_path), f"Calibration doc missing at {doc_path}")

        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Epistemic framework assertions
        self.assertIn("Truth Engine", content)
        self.assertIn("WHAT WE OBSERVE", content)
        self.assertIn("WHAT WE DERIVE", content)
        self.assertIn("WHAT WE INFER", content)
        self.assertIn("WHAT WE VERIFY", content)

        # Empirical data assertions
        self.assertIn("373", content)
        self.assertIn("run_verification_loop.py", content)
        self.assertIn("server.py", content)
        self.assertIn("analyzer.py", content)

        # Scientific limitation honesty assertion
        self.assertIn("heuristic", content.lower())
        self.assertTrue("N \\ge 50" in content or "N >= 50" in content, "Must cite N >= 50 requirement")

    def test_fixture_correlation_bounds(self):
        """Assert risk tiering bounds on benchmark fixtures."""
        # 1. Clean repo: 0 HIGH risk files
        clean_path = os.path.join(self.fixtures_dir, "clean_repo")
        clean_cb = analyze_directory(clean_path)
        clean_risks = evaluate_risks(clean_cb, list(clean_cb.keys()), repo_path=clean_path)
        high_clean = [r for r in clean_risks if r.level == "HIGH"]
        self.assertEqual(len(high_clean), 0, f"clean_repo must produce 0 HIGH risk files, got {len(high_clean)}")

        # 2. Tangled repo: god_module.py is rank 1 HIGH risk
        tangled_path = os.path.join(self.fixtures_dir, "tangled_repo")
        tangled_cb = analyze_directory(tangled_path)
        tangled_risks = evaluate_risks(tangled_cb, list(tangled_cb.keys()), repo_path=tangled_path)
        tangled_sorted = sorted(tangled_risks, key=lambda r: -r.impact_score)
        self.assertIn("god_module.py", tangled_sorted[0].file_path)
        self.assertEqual(tangled_sorted[0].level, "HIGH")

        # 3. Mixed repo: exactly 2 planted files are HIGH risk
        mixed_path = os.path.join(self.fixtures_dir, "mixed_repo")
        mixed_cb = analyze_directory(mixed_path)
        mixed_risks = evaluate_risks(mixed_cb, list(mixed_cb.keys()), repo_path=mixed_path)
        high_mixed = [r for r in mixed_risks if r.level == "HIGH"]
        self.assertEqual(len(high_mixed), 2, f"mixed_repo must have exactly 2 HIGH risk files, got {len(high_mixed)}")
        high_paths = {os.path.basename(r.file_path) for r in high_mixed}
        self.assertEqual(high_paths, {"risky_core.py", "risky_dispatcher.py"})

    def test_confidence_degradation_honesty(self):
        """Assert that missing signals honestly degrade in signals block without silent simulation."""
        import tempfile
        with tempfile.TemporaryDirectory() as non_git_dir:
            sample_file = os.path.join(non_git_dir, "sample.py")
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("def sample():\n    return 42\n")

            clean_cb = analyze_directory(non_git_dir)
            # Isolated directory outside git has no git commit history and no coverage artifacts
            risks = evaluate_risks(clean_cb, list(clean_cb.keys()), repo_path=non_git_dir)
            self.assertGreater(len(risks), 0)
            
            sample = risks[0]
            signals = sample.signals
            
            # AST and Coupling are active
            self.assertEqual(signals["ast"]["status"], "active")
            self.assertEqual(signals["coupling"]["status"], "active")

            # Churn and Coverage must be unavailable
            self.assertEqual(signals["churn"]["status"], "unavailable")
            self.assertEqual(signals["coverage"]["status"], "unavailable")

            # Sum of active weights reflects available evidence: 0.35 + 0.25 = 0.60
            active_weight_sum = sum(
                s["weight"] for s in signals.values() if s["status"] == "active"
            )
            self.assertAlmostEqual(active_weight_sum, 0.60, places=4)

    def test_truth_engine_signal_categories(self):
        """Assert programmatic epistemic metadata maps each signal to its Truth Engine tier."""
        expected_tiers = {
            "ast": "OBSERVED",
            "coupling": "DERIVED",
            "churn": "INFERRED",
            "coverage": "VERIFIED",
        }

        for sig, tier in expected_tiers.items():
            self.assertIn(sig, CONFIDENCE_METADATA)
            self.assertEqual(CONFIDENCE_METADATA[sig]["tier"], tier)

        # Check that evaluate_risks attaches the tier to AnalysisPacket.signals
        clean_path = os.path.join(self.fixtures_dir, "clean_repo")
        clean_cb = analyze_directory(clean_path)
        risks = evaluate_risks(clean_cb, list(clean_cb.keys()), repo_path=clean_path)
        sample = risks[0]

        for sig, tier in expected_tiers.items():
            self.assertIn(sig, sample.signals)
            self.assertEqual(sample.signals[sig]["tier"], tier)


if __name__ == "__main__":
    unittest.main()
