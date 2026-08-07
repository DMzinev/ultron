"""
Ultron Unit Tests for Closed-Loop Outcome Tracker Engine
"""
import unittest
from ultron.core.rkm.outcome_tracker import OutcomeTracker

class TestOutcomeTracker(unittest.TestCase):
    def test_calculate_actual_reduction(self):
        # Baseline 20, Current 10 -> 50% reduction
        red = OutcomeTracker.calculate_actual_reduction(20.0, 10.0)
        self.assertEqual(red, 50.0)

    def test_evaluate_refactoring_outcome_accurate(self):
        # Predicted 35%, Actual 30% (from 20 -> 14) -> Variance 5% (Accurate)
        res = OutcomeTracker.evaluate_refactoring_outcome("ultron/core/analyzer.py", 20.0, 14.0, 35.0)
        self.assertEqual(res["status"], "active")
        self.assertEqual(res["actual_reduction_pct"], 30.0)
        self.assertEqual(res["variance_pct"], 5.0)
        self.assertTrue(res["prediction_accurate"])

    def test_zero_baseline_clamp_guard(self):
        res = OutcomeTracker.evaluate_refactoring_outcome("test.py", 0.0, 5.0, 20.0)
        self.assertEqual(res["status"], "active")
        self.assertIsInstance(res["actual_reduction_pct"], float)

if __name__ == "__main__":
    unittest.main()
