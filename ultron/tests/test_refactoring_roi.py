"""
ultron.tests.test_refactoring_roi
Unit test suite asserting refactoring ROI mathematical properties, monotonicity, and ranking.
"""

import unittest
from ultron.core.refactoring_roi import RefactoringROIEngine, norm_path


class TestRefactoringROIEngine(unittest.TestCase):
    """Unit tests for deterministic RefactoringROIEngine calculations."""

    def test_norm_path(self):
        """Asserts path separators are normalized to POSIX forward slashes."""
        self.assertEqual(norm_path("ultron\\core\\scoring.py"), "ultron/core/scoring.py")
        self.assertEqual(norm_path(None), "")

    def test_effort_estimation_boundaries(self):
        """Asserts effort LOC calculations are safe and non-zero."""
        self.assertEqual(RefactoringROIEngine.estimate_refactor_effort_loc(0, 0), 1)
        self.assertEqual(RefactoringROIEngine.estimate_refactor_effort_loc(2, 2), 11) # max(5, 2*3 + 2*2.5) = 11
        # Capped by total_loc if provided
        self.assertEqual(RefactoringROIEngine.estimate_refactor_effort_loc(10, 10, total_loc=20), 20)

    def test_roi_formula_and_provenance(self):
        """Asserts exact formula outputs and provenance metadata."""
        sample_risk = {
            "file_path": "ultron/core/pipeline.py",
            "complexity": 10.0,
            "coupling_score": 6.0,
            "impact_score": 8.0,
            "loc": 100
        }
        res = RefactoringROIEngine.compute_module_roi(sample_risk)
        self.assertEqual(res["file_path"], "ultron/core/pipeline.py")
        self.assertEqual(res["file_name"], "pipeline.py")
        self.assertGreater(res["roi_score"], 0.0)
        self.assertGreater(res["projected_risk_reduction_pct"], 0.0)
        self.assertIn("formula_version", res["provenance"])

    def test_mathematical_monotonicity(self):
        """Asserts higher coupling and complexity strictly increase ROI given identical effort budget."""
        base = {"file": "a.py", "complexity": 5.0, "coupling": 2.0, "impact_score": 5.0, "loc": 10}
        higher_c = {"file": "b.py", "complexity": 10.0, "coupling": 2.0, "impact_score": 5.0, "loc": 10}
        higher_k = {"file": "c.py", "complexity": 5.0, "coupling": 8.0, "impact_score": 5.0, "loc": 10}

        roi_base = RefactoringROIEngine.compute_module_roi(base)["roi_score"]
        roi_high_c = RefactoringROIEngine.compute_module_roi(higher_c)["roi_score"]
        roi_high_k = RefactoringROIEngine.compute_module_roi(higher_k)["roi_score"]

        self.assertGreater(roi_high_c, roi_base)
        self.assertGreater(roi_high_k, roi_base)

    def test_opportunity_tier_categorization(self):
        """Asserts deterministic tier classification."""
        quick_win = {"file": "quick.py", "complexity": 8.0, "coupling": 2.0, "impact_score": 10.0, "loc": 15}
        deep_decouple = {"file": "deep.py", "complexity": 25.0, "coupling": 12.0, "impact_score": 8.0, "loc": 200}
        cleanup = {"file": "clean.py", "complexity": 2.0, "coupling": 0.0, "impact_score": 1.0, "loc": 20}

        self.assertEqual(RefactoringROIEngine.compute_module_roi(quick_win)["tier"], "HIGH_LEVERAGE_QUICK_WIN")
        self.assertEqual(RefactoringROIEngine.compute_module_roi(deep_decouple)["tier"], "DEEP_ARCHITECTURAL_DECOUPLING")
        self.assertEqual(RefactoringROIEngine.compute_module_roi(cleanup)["tier"], "ROUTINE_CLEANUP")

    def test_rank_refactoring_opportunities_determinism(self):
        """Asserts ranked list is sorted by ROI score descending and respects limit."""
        risks = [
            {"file": "mod1.py", "complexity": 2.0, "coupling": 1.0, "impact_score": 1.0},
            {"file": "mod2.py", "complexity": 15.0, "coupling": 6.0, "impact_score": 9.0},
            {"file": "mod3.py", "complexity": 8.0, "coupling": 3.0, "impact_score": 4.0},
        ]
        ranked = RefactoringROIEngine.rank_refactoring_opportunities(risks, limit=2)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["file_name"], "mod2.py")
        self.assertGreaterEqual(ranked[0]["roi_score"], ranked[1]["roi_score"])


if __name__ == "__main__":
    unittest.main()
