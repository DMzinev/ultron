"""
Ultron Unit Tests for Refactoring Impact & Maintenance Cost Estimator
"""
import unittest
from ultron.core.rkm.refactor_estimator import RefactorEstimator

class TestRefactorEstimator(unittest.TestCase):
    def test_cost_reduction_calculation_high_complexity(self):
        # Current complexity=20, coupling=10 (prod=200). Target=10. Reduction = 100 * (1 - 10/200) = 95% -> capped at 75.0%
        red = RefactorEstimator.calculate_cost_reduction(20, 10)
        self.assertEqual(red, 75.0)

    def test_cost_reduction_calculation_low_complexity(self):
        # Current complexity=5, coupling=2 (prod=10). Target=10. Reduction = 100 * (1 - 10/10) = 0%
        red = RefactorEstimator.calculate_cost_reduction(5, 2)
        self.assertEqual(red, 0.0)

    def test_zero_complexity_coupling_guard(self):
        red = RefactorEstimator.calculate_cost_reduction(0, 0)
        self.assertGreaterEqual(red, 0.0)
        self.assertLessEqual(red, 75.0)

    def test_generate_refactoring_plan(self):
        plan = RefactorEstimator.generate_refactoring_plan("ultron/core/analyzer.py", 18, 9, 8.5)
        self.assertEqual(plan["refactor_tier"], "HIGH")
        self.assertGreater(plan["estimated_maintenance_cost_reduction_pct"], 0.0)
        self.assertGreater(len(plan["action_plan_steps"]), 0)

if __name__ == "__main__":
    unittest.main()
